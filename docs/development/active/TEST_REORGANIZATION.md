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
├── README.md                    # AUTO-GENERATED: Test catalog with metrics
├── conftest.py                  # Shared fixtures, markers
│                                # NOTE: Targets live in config/defaults.yaml (hub_ci.thresholds)
│
├── unit/                        # Fast, isolated, no I/O
│   ├── commands/                # One file per command module
│   │   ├── test_detect.py
│   │   ├── test_validate.py
│   │   ├── test_init.py
│   │   └── ...
│   ├── services/
│   │   ├── ci_engine/           # Split from monolithic test_ci_engine.py
│   │   │   ├── test_ci_engine_project_detection.py
│   │   │   ├── test_ci_engine_tool_state.py
│   │   │   ├── test_ci_engine_notifications.py
│   │   │   ├── test_ci_engine_runners.py
│   │   │   └── test_ci_engine_gates.py
│   │   ├── ci_runner/           # Split from monolithic test_ci_runner.py
│   │   │   ├── test_ci_runner_core.py
│   │   │   ├── test_ci_runner_parsers.py
│   │   │   ├── test_ci_runner_python.py
│   │   │   └── test_ci_runner_java.py
│   │   ├── test_triage_service.py
│   │   └── ...
│   ├── hub_ci/                  # Split from monolithic test_hub_ci*.py files
│   │   ├── test_hub_ci_helpers.py
│   │   ├── test_hub_ci_linting.py
│   │   ├── test_hub_ci_badges.py
│   │   ├── test_hub_ci_validation.py
│   │   ├── test_hub_ci_smoke.py
│   │   ├── test_hub_ci_release_platform.py
│   │   ├── test_hub_ci_release_install.py
│   │   ├── test_hub_ci_release_analysis.py
│   │   └── test_hub_ci_release_commands.py
│   ├── docs/                    # Docs automation tests (see `tests/unit/docs/`)
│   ├── core/
│   │   ├── languages/
│   │   │   ├── test_language_strategies.py
│   │   │   ├── test_pom_parsing.py
│   │   │   ├── test_pom_tools.py
│   │   │   └── test_python_ci_badges.py
│   │   ├── output/
│   │   │   ├── test_output_context.py
│   │   │   └── test_output_renderers.py
│   │   ├── diagnostics/
│   │   │   ├── test_diagnostics.py
│   │   │   ├── test_correlation.py
│   │   │   └── test_debug_utils.py
│   │   ├── test_gate_specs.py
│   │   ├── test_ci_report.py
│   │   └── ...
│   └── config/
│       ├── test_schema.py
│       ├── test_normalize.py
│       └── ...
│
├── integration/                 # Cross-module, may use filesystem
│   ├── test_config_pipeline.py  # Config cascade integration
│   ├── test_integration_check.py # Check command integration
│   ├── test_services_aggregation.py # Report aggregation workflow
│   ├── repo_shapes/             # Repo shape tests
│   └── wizard/                  # Wizard flow tests
│
├── e2e/                         # Full workflows, slow
│   ├── test_e2e_smoke.py
│   ├── test_cli_integration.py
│   ├── test_setup_flow.py
│   └── test_triage_integration.py
│
├── contracts/                   # Schema/API contract tests
│   ├── test_command_output_contract.py
│   ├── test_schema_contract.py
│   ├── test_cli_parser_contracts.py
│   ├── test_json_purity.py
│   └── ...
│
├── property/                    # Hypothesis property-based tests
│   ├── test_property_based.py
│   ├── test_property_based_extended.py
│   └── ...
│
├── regression/                  # Bug reproduction tests
│   ├── test_issue_001_yaml_parse.py
│   └── ...
│
├── performance/                 # Benchmark tests
│   └── test_performance.py
│
├── validation/                  # Input validation tests
│   ├── test_validation.py
│   └── test_validate_config.py
│
└── snapshots/                   # Snapshot test data
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

Reads coverage and mutation results and updates each test file's
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
- All test files follow naming conventions
- TEST-METRICS blocks are present
- Module docstrings and import consistency
- Template structure compliance
"""
```

**Runs:** In CI. `--strict` enabled in `hub-production-ci.yml` (2026-01-17).

### CLI Wrapper (`cihub hub-ci test-metrics`)

Runs update + README + drift checks with consistent CI behavior.

- `--write` updates metrics and README (main-only by default).
- `--strict` makes drift warnings fail the run.
- Defaults to check-only mode for PRs.

---

## Migration Plan

### Phase 1: Infrastructure (Day 1)
- [x] Add `cihub hub-ci thresholds` command (read/write to config/defaults.yaml)
- [x] Add per-module override support to config/defaults.yaml schema
- [x] Create `scripts/update_test_metrics.py` (reads targets from config/defaults.yaml)
- [x] Create `scripts/generate_test_readme.py`
- [x] Create `scripts/check_test_drift.py`
- [x] Add to CI workflow (hub-production-ci.yml)
- [x] Seed test metrics + README; validate `cihub hub-ci test-metrics --strict` (2026-01-17)
- [x] Enable `cihub hub-ci test-metrics --strict` in CI (2026-01-17)
- [x] Add schema-sync fallback defaults regression coverage (gates/reports/feature flags)

### Phase 2: Directory Structure (Day 2) — ✅ COMPLETED 2026-01-17
- [x] Create new directory structure (`unit/`, `integration/`, etc.)
- [x] Move contract tests to `contracts/`
- [x] Move e2e tests to `e2e/`
- [x] Update imports in moved files

### Phase 3: Unit Test Reorganization (Days 3-5) — ✅ COMPLETED 2026-01-17
- [x] Split `test_commands.py` into `unit/commands/test_*.py`
- [x] Split `test_services_*.py` into `unit/services/test_*.py`
- [x] Split `test_config_*.py` into `unit/config/test_*.py`
- [x] Add parameterized tests where applicable
- [x] Add descriptive test IDs
- [x] Fix contract test command path resolution + hub-ci release platform mocks after file moves (2026-01-17)

### Phase 4: Property Tests (Day 6)
- [x] Identify pure functions suitable for Hypothesis (config input generation, path/threshold validators)
- [x] Create `property/` tests for config parsing (generate_workflow_inputs invariants)
- [x] Create `property/` tests for validators (validate_subdir, threshold key validation)
- [ ] Target: 5% of tests are property-based (pending metrics refresh)

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

- **164 total files** in `tests/` directory (155 test files + 9 supporting files) — file count only
- **164 files (100%)** map cleanly to proposed categories
- **0 files** require splitting before moving (splits complete)
- **4 files** with excellent cohesion kept as-is despite size

### Directory Categories (Current Structure)

All categories in the proposed structure are now present.
Optional future additions:
```
tests/unit/templates/ # Template rendering tests (none yet)
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

New step required in `hub-production-ci.yml`:
1. `cihub hub-ci test-metrics` - run after mutation tests to use coverage + mutmut inputs; strict enabled (2026-01-17)

### Large Monolithic Files

Split before moving (see "Monolithic File Split Plan" below for details):
- `test_ci_engine.py` → `tests/unit/services/ci_engine/test_ci_engine_*.py` (5 files) ✅ **COMPLETED 2026-01-17**
- `test_hub_ci.py` → 6 files in `tests/unit/hub_ci/` (helpers, linting, badges, validation, smoke, release_*) ✅ **COMPLETED 2026-01-17**
- `test_hub_ci_release.py` → 4 files in `tests/unit/hub_ci/` (release_*) ✅ **COMPLETED 2026-01-17**
- `test_ci_runner.py` → `tests/unit/services/ci_runner/test_ci_runner_{core,parsers,python,java}.py` ✅ **COMPLETED 2026-01-17**
- `test_docs_stale.py` → `tests/unit/docs/test_docs_stale_*.py` (4 files) ✅ **COMPLETED 2026-01-17**

**Kept as-is (good cohesion):** `tests/unit/config/test_config_module.py`, `tests/unit/commands/test_commands_adr.py`, `tests/unit/services/test_registry_service_threshold_mapping.py`

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
- [x] Create comprehensive file mapping (all 164 files → new homes) — **COMPLETED 2026-01-17**
- [x] Split large monolithic test files (see "Monolithic File Split Plan" below) — **COMPLETED 2026-01-17**
- [x] Register pytest markers in pyproject.toml

---

## Phase 0: Comprehensive File Mapping (164 Files)

> **Completed:** 2026-01-17 | **Author:** 8-Agent Parallel Analysis
>
> **Note:** Original estimate was 78 files. Actual count is **164 files** including:
> - 155 `test_*.py` files
> - 9 supporting files (`conftest.py`, `__init__.py`, snapshots)
> - File counts only (not test counts), derived from `rg --files tests`

### Supporting Files (Keep in Place)

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/conftest.py` | `tests/conftest.py` | fixture | Shared fixture config; keep near related tests. |
| `tests/contracts/__init__.py` | `tests/contracts/__init__.py` | marker | Package marker; keep near related tests. |
| `tests/integration/repo_shapes/__init__.py` | `tests/integration/repo_shapes/__init__.py` | marker | Package marker; keep near related tests. |
| `tests/integration/repo_shapes/conftest.py` | `tests/integration/repo_shapes/conftest.py` | fixture | Shared fixture config; keep near related tests. |
| `tests/integration/wizard/__init__.py` | `tests/integration/wizard/__init__.py` | marker | Package marker; keep near related tests. |
| `tests/snapshots/__snapshots__/test_cli_snapshots.ambr` | `tests/snapshots/__snapshots__/test_cli_snapshots.ambr` | snapshot | Snapshot artifact for snapshot tests. |
| `tests/snapshots/cli_help.txt` | `tests/snapshots/cli_help.txt` | snapshot | Snapshot artifact for snapshot tests. |
| `tests/unit/config/__init__.py` | `tests/unit/config/__init__.py` | marker | Package marker; keep near related tests. |
| `tests/unit/services/__init__.py` | `tests/unit/services/__init__.py` | marker | Package marker; keep near related tests. |

### Contract Tests → `tests/contracts/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/contracts/test_cli_parser_contracts.py` | `tests/contracts/test_cli_parser_contracts.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_command_output_contract.py` | `tests/contracts/test_command_output_contract.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_contract_command_result.py` | `tests/contracts/test_contract_command_result.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_contract_consistency.py` | `tests/contracts/test_contract_consistency.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_json_purity.py` | `tests/contracts/test_json_purity.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_migrated_commands_contract.py` | `tests/contracts/test_migrated_commands_contract.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_registry_schema_contract.py` | `tests/contracts/test_registry_schema_contract.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_schema_contract.py` | `tests/contracts/test_schema_contract.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_schema_fields.py` | `tests/contracts/test_schema_fields.py` | contract | Contract coverage for CLI/schema/workflow outputs. |
| `tests/contracts/test_workflow_contract.py` | `tests/contracts/test_workflow_contract.py` | contract | Contract coverage for CLI/schema/workflow outputs. |

### E2E Tests → `tests/e2e/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/e2e/test_cli_integration.py` | `tests/e2e/test_cli_integration.py` | e2e | End-to-end workflow coverage. |
| `tests/e2e/test_e2e_smoke.py` | `tests/e2e/test_e2e_smoke.py` | e2e | End-to-end workflow coverage. |
| `tests/e2e/test_setup_flow.py` | `tests/e2e/test_setup_flow.py` | e2e | End-to-end workflow coverage. |
| `tests/e2e/test_triage_integration.py` | `tests/e2e/test_triage_integration.py` | e2e | End-to-end workflow coverage. |

### Property-Based Tests → `tests/property/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/property/test_property_based.py` | `tests/property/test_property_based.py` | property | Hypothesis property-based coverage. |
| `tests/property/test_property_based_extended.py` | `tests/property/test_property_based_extended.py` | property | Hypothesis property-based coverage. |
| `tests/property/test_registry_roundtrip_invariant.py` | `tests/property/test_registry_roundtrip_invariant.py` | property | Hypothesis property-based coverage. |
| `tests/property/test_triage_properties.py` | `tests/property/test_triage_properties.py` | property | Hypothesis property-based coverage. |

### Snapshot Tests → `tests/snapshots/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/snapshots/test_cli_snapshots.py` | `tests/snapshots/test_cli_snapshots.py` | snapshot | Snapshot stability for CLI/report output. |
| `tests/snapshots/test_module_structure.py` | `tests/snapshots/test_module_structure.py` | snapshot | Snapshot stability for CLI/report output. |
| `tests/snapshots/test_summary_commands.py` | `tests/snapshots/test_summary_commands.py` | snapshot | Snapshot stability for CLI/report output. |

### Integration Tests → `tests/integration/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/integration/repo_shapes/test_ci_shapes.py` | `tests/integration/repo_shapes/test_ci_shapes.py` | integration | Cross-module integration coverage. |
| `tests/integration/repo_shapes/test_detect_shapes.py` | `tests/integration/repo_shapes/test_detect_shapes.py` | integration | Cross-module integration coverage. |
| `tests/integration/repo_shapes/test_init_shapes.py` | `tests/integration/repo_shapes/test_init_shapes.py` | integration | Cross-module integration coverage. |
| `tests/integration/test_config_pipeline.py` | `tests/integration/test_config_pipeline.py` | integration | Cross-module integration coverage. |
| `tests/integration/test_fixture_repo_shapes.py` | `tests/integration/test_fixture_repo_shapes.py` | integration | Cross-module integration coverage. |
| `tests/integration/test_integration_check.py` | `tests/integration/test_integration_check.py` | integration | Cross-module integration coverage. |
| `tests/integration/test_services_aggregation.py` | `tests/integration/test_services_aggregation.py` | integration | Cross-module integration coverage. |
| `tests/integration/test_template_drift.py` | `tests/integration/test_template_drift.py` | integration | Cross-module integration coverage. |
| `tests/integration/test_templates.py` | `tests/integration/test_templates.py` | integration | Cross-module integration coverage. |
| `tests/integration/wizard/test_cli_wizard_parity.py` | `tests/integration/wizard/test_cli_wizard_parity.py` | integration | Cross-module integration coverage. |
| `tests/integration/wizard/test_profile_selection.py` | `tests/integration/wizard/test_profile_selection.py` | integration | Cross-module integration coverage. |
| `tests/integration/wizard/test_wizard_modules.py` | `tests/integration/wizard/test_wizard_modules.py` | integration | Cross-module integration coverage. |

### Regression Tests → `tests/regression/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/regression/test_triage_detection.py` | `tests/regression/test_triage_detection.py` | regression | Regression coverage for known bug. |

### Performance Tests → `tests/performance/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/performance/test_performance.py` | `tests/performance/test_performance.py` | performance | Benchmark/performance coverage. |

### Validation Tests → `tests/validation/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/validation/test_validate_config.py` | `tests/validation/test_validate_config.py` | validation | Input/config validation coverage. |
| `tests/validation/test_validation.py` | `tests/validation/test_validation.py` | validation | Input/config validation coverage. |

### Unit Tests: Commands → `tests/unit/commands/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/commands/test_commands.py` | `tests/unit/commands/test_commands.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_adr.py` | `tests/unit/commands/test_commands_adr.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_check.py` | `tests/unit/commands/test_commands_check.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_ci.py` | `tests/unit/commands/test_commands_ci.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_discover.py` | `tests/unit/commands/test_commands_discover.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_dispatch.py` | `tests/unit/commands/test_commands_dispatch.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_docs.py` | `tests/unit/commands/test_commands_docs.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_extended.py` | `tests/unit/commands/test_commands_extended.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_new.py` | `tests/unit/commands/test_commands_new.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_preflight.py` | `tests/unit/commands/test_commands_preflight.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_scaffold.py` | `tests/unit/commands/test_commands_scaffold.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_smoke.py` | `tests/unit/commands/test_commands_smoke.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_commands_templates.py` | `tests/unit/commands/test_commands_templates.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_config_cmd.py` | `tests/unit/commands/test_config_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_fix_command.py` | `tests/unit/commands/test_fix_command.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_fix_unit.py` | `tests/unit/commands/test_fix_unit.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_gradle_cmd.py` | `tests/unit/commands/test_gradle_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_pom_cmd.py` | `tests/unit/commands/test_pom_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_profile_cmd.py` | `tests/unit/commands/test_profile_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_registry_cmd.py` | `tests/unit/commands/test_registry_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_repo_cmd.py` | `tests/unit/commands/test_repo_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_run.py` | `tests/unit/commands/test_run.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_scaffold_github.py` | `tests/unit/commands/test_scaffold_github.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_secrets.py` | `tests/unit/commands/test_secrets.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_smoke_command.py` | `tests/unit/commands/test_smoke_command.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_threshold_cmd.py` | `tests/unit/commands/test_threshold_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_tool_cmd.py` | `tests/unit/commands/test_tool_cmd.py` | unit | Unit tests for CLI command handlers. |
| `tests/unit/commands/test_tool_cmd_extended.py` | `tests/unit/commands/test_tool_cmd_extended.py` | unit | Unit tests for CLI command handlers. |

### Unit Tests: Services/CI Engine → `tests/unit/services/ci_engine/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/services/ci_engine/test_ci_engine_gates.py` | `tests/unit/services/ci_engine/test_ci_engine_gates.py` | unit | Unit tests for CI engine behavior. |
| `tests/unit/services/ci_engine/test_ci_engine_notifications.py` | `tests/unit/services/ci_engine/test_ci_engine_notifications.py` | unit | Unit tests for CI engine behavior. |
| `tests/unit/services/ci_engine/test_ci_engine_project_detection.py` | `tests/unit/services/ci_engine/test_ci_engine_project_detection.py` | unit | Unit tests for CI engine behavior. |
| `tests/unit/services/ci_engine/test_ci_engine_runners.py` | `tests/unit/services/ci_engine/test_ci_engine_runners.py` | unit | Unit tests for CI engine behavior. |
| `tests/unit/services/ci_engine/test_ci_engine_tool_state.py` | `tests/unit/services/ci_engine/test_ci_engine_tool_state.py` | unit | Unit tests for CI engine behavior. |

### Unit Tests: Services/CI Runner → `tests/unit/services/ci_runner/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/services/ci_runner/test_ci_runner_core.py` | `tests/unit/services/ci_runner/test_ci_runner_core.py` | unit | Unit tests for CI runner execution/parsing. |
| `tests/unit/services/ci_runner/test_ci_runner_java.py` | `tests/unit/services/ci_runner/test_ci_runner_java.py` | unit | Unit tests for CI runner execution/parsing. |
| `tests/unit/services/ci_runner/test_ci_runner_parsers.py` | `tests/unit/services/ci_runner/test_ci_runner_parsers.py` | unit | Unit tests for CI runner execution/parsing. |
| `tests/unit/services/ci_runner/test_ci_runner_python.py` | `tests/unit/services/ci_runner/test_ci_runner_python.py` | unit | Unit tests for CI runner execution/parsing. |

### Unit Tests: Services → `tests/unit/services/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/services/test_ai_loop.py` | `tests/unit/services/test_ai_loop.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_ai_patterns.py` | `tests/unit/services/test_ai_patterns.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_registry_cross_root.py` | `tests/unit/services/test_registry_cross_root.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_registry_service.py` | `tests/unit/services/test_registry_service.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_registry_service_threshold_mapping.py` | `tests/unit/services/test_registry_service_threshold_mapping.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_services_ci.py` | `tests/unit/services/test_services_ci.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_services_configuration.py` | `tests/unit/services/test_services_configuration.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_services_discovery.py` | `tests/unit/services/test_services_discovery.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_services_report_summary.py` | `tests/unit/services/test_services_report_summary.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_services_report_validator.py` | `tests/unit/services/test_services_report_validator.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_triage_evidence.py` | `tests/unit/services/test_triage_evidence.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_triage_github.py` | `tests/unit/services/test_triage_github.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_triage_log_parser.py` | `tests/unit/services/test_triage_log_parser.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_triage_service.py` | `tests/unit/services/test_triage_service.py` | unit | Unit tests for service layer. |
| `tests/unit/services/test_triage_verification.py` | `tests/unit/services/test_triage_verification.py` | unit | Unit tests for service layer. |

### Unit Tests: Config → `tests/unit/config/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/config/test_apply_profile.py` | `tests/unit/config/test_apply_profile.py` | unit | Unit tests for config loading/merging. |
| `tests/unit/config/test_ci_config.py` | `tests/unit/config/test_ci_config.py` | unit | Unit tests for config loading/merging. |
| `tests/unit/config/test_config_module.py` | `tests/unit/config/test_config_module.py` | unit | Unit tests for config loading/merging. |
| `tests/unit/config/test_config_outputs.py` | `tests/unit/config/test_config_outputs.py` | unit | Unit tests for config loading/merging. |
| `tests/unit/config/test_merge_order.py` | `tests/unit/config/test_merge_order.py` | unit | Unit tests for config loading/merging. |
| `tests/unit/config/test_repo_config.py` | `tests/unit/config/test_repo_config.py` | unit | Unit tests for config loading/merging. |
| `tests/unit/config/test_schema_sync.py` | `tests/unit/config/test_schema_sync.py` | unit | Unit tests for config loading/merging. |

### Unit Tests: Core → `tests/unit/core/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/core/test_ci_env_overrides.py` | `tests/unit/core/test_ci_env_overrides.py` | unit | Unit tests for core utilities. |
| `tests/unit/core/test_ci_report.py` | `tests/unit/core/test_ci_report.py` | unit | Unit tests for core utilities. |
| `tests/unit/core/test_ci_self_validate.py` | `tests/unit/core/test_ci_self_validate.py` | unit | Unit tests for core utilities. |
| `tests/unit/core/test_fail_on_normalization.py` | `tests/unit/core/test_fail_on_normalization.py` | unit | Unit tests for core utilities. |
| `tests/unit/core/test_gate_specs.py` | `tests/unit/core/test_gate_specs.py` | unit | Unit tests for core utilities. |
| `tests/unit/core/test_init_override.py` | `tests/unit/core/test_init_override.py` | unit | Unit tests for core utilities. |
| `tests/unit/core/test_workflow_lint.py` | `tests/unit/core/test_workflow_lint.py` | unit | Unit tests for core utilities. |

### Unit Tests: Core/Languages → `tests/unit/core/languages/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/core/languages/test_language_strategies.py` | `tests/unit/core/languages/test_language_strategies.py` | unit | Unit tests for language strategy logic. |
| `tests/unit/core/languages/test_pom_parsing.py` | `tests/unit/core/languages/test_pom_parsing.py` | unit | Unit tests for language strategy logic. |
| `tests/unit/core/languages/test_pom_tools.py` | `tests/unit/core/languages/test_pom_tools.py` | unit | Unit tests for language strategy logic. |
| `tests/unit/core/languages/test_python_ci_badges.py` | `tests/unit/core/languages/test_python_ci_badges.py` | unit | Unit tests for language strategy logic. |

### Unit Tests: Core/Output → `tests/unit/core/output/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/core/output/test_output_context.py` | `tests/unit/core/output/test_output_context.py` | unit | Unit tests for output rendering/context. |
| `tests/unit/core/output/test_output_renderers.py` | `tests/unit/core/output/test_output_renderers.py` | unit | Unit tests for output rendering/context. |

### Unit Tests: Core/Diagnostics → `tests/unit/core/diagnostics/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/core/diagnostics/test_correlation.py` | `tests/unit/core/diagnostics/test_correlation.py` | unit | Unit tests for diagnostics helpers. |
| `tests/unit/core/diagnostics/test_debug_utils.py` | `tests/unit/core/diagnostics/test_debug_utils.py` | unit | Unit tests for diagnostics helpers. |
| `tests/unit/core/diagnostics/test_diagnostics.py` | `tests/unit/core/diagnostics/test_diagnostics.py` | unit | Unit tests for diagnostics helpers. |

### Unit Tests: Utils → `tests/unit/utils/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/utils/test_env_registry.py` | `tests/unit/utils/test_env_registry.py` | unit | Unit tests for shared utilities. |
| `tests/unit/utils/test_env_toggles.py` | `tests/unit/utils/test_env_toggles.py` | unit | Unit tests for shared utilities. |
| `tests/unit/utils/test_env_utils.py` | `tests/unit/utils/test_env_utils.py` | unit | Unit tests for shared utilities. |
| `tests/unit/utils/test_exec_utils.py` | `tests/unit/utils/test_exec_utils.py` | unit | Unit tests for shared utilities. |
| `tests/unit/utils/test_fs_utils.py` | `tests/unit/utils/test_fs_utils.py` | unit | Unit tests for shared utilities. |
| `tests/unit/utils/test_progress_utils.py` | `tests/unit/utils/test_progress_utils.py` | unit | Unit tests for shared utilities. |
| `tests/unit/utils/test_script_shims.py` | `tests/unit/utils/test_script_shims.py` | unit | Unit tests for shared utilities. |
| `tests/unit/utils/test_utils_project.py` | `tests/unit/utils/test_utils_project.py` | unit | Unit tests for shared utilities. |

### Unit Tests: Wizard → `tests/unit/wizard/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/wizard/test_wizard_questions.py` | `tests/unit/wizard/test_wizard_questions.py` | unit | Unit tests for wizard questions/validators. |
| `tests/unit/wizard/test_wizard_validators.py` | `tests/unit/wizard/test_wizard_validators.py` | unit | Unit tests for wizard questions/validators. |

### Unit Tests: Hub CI → `tests/unit/hub_ci/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/hub_ci/test_hub_ci_badges.py` | `tests/unit/hub_ci/test_hub_ci_badges.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_helpers.py` | `tests/unit/hub_ci/test_hub_ci_helpers.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_linting.py` | `tests/unit/hub_ci/test_hub_ci_linting.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_mutmut.py` | `tests/unit/hub_ci/test_hub_ci_mutmut.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_python_tools.py` | `tests/unit/hub_ci/test_hub_ci_python_tools.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_release_analysis.py` | `tests/unit/hub_ci/test_hub_ci_release_analysis.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_release_commands.py` | `tests/unit/hub_ci/test_hub_ci_release_commands.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_release_install.py` | `tests/unit/hub_ci/test_hub_ci_release_install.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_release_platform.py` | `tests/unit/hub_ci/test_hub_ci_release_platform.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_security.py` | `tests/unit/hub_ci/test_hub_ci_security.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_smoke.py` | `tests/unit/hub_ci/test_hub_ci_smoke.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_test_metrics.py` | `tests/unit/hub_ci/test_hub_ci_test_metrics.py` | unit | Unit tests for hub-ci test metrics automation. |
| `tests/unit/hub_ci/test_hub_ci_validation.py` | `tests/unit/hub_ci/test_hub_ci_validation.py` | unit | Unit tests for hub-ci command implementations. |
| `tests/unit/hub_ci/test_hub_ci_zizmor_license.py` | `tests/unit/hub_ci/test_hub_ci_zizmor_license.py` | unit | Unit tests for hub-ci command implementations. |

### Unit Tests: CLI → `tests/unit/cli/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/cli/test_cihub_cli.py` | `tests/unit/cli/test_cihub_cli.py` | unit | Unit tests for CLI parser/dispatch. |
| `tests/unit/cli/test_cli_command_matrix.py` | `tests/unit/cli/test_cli_command_matrix.py` | unit | Unit tests for CLI parser/dispatch. |
| `tests/unit/cli/test_cli_commands.py` | `tests/unit/cli/test_cli_commands.py` | unit | Unit tests for CLI parser/dispatch. |
| `tests/unit/cli/test_cli_common.py` | `tests/unit/cli/test_cli_common.py` | unit | Unit tests for CLI parser/dispatch. |
| `tests/unit/cli/test_cli_debug.py` | `tests/unit/cli/test_cli_debug.py` | unit | Unit tests for CLI parser/dispatch. |

### Unit Tests: Reports → `tests/unit/reports/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/reports/test_aggregate_reports.py` | `tests/unit/reports/test_aggregate_reports.py` | unit | Unit tests for report aggregation/validation. |
| `tests/unit/reports/test_report.py` | `tests/unit/reports/test_report.py` | unit | Unit tests for report aggregation/validation. |
| `tests/unit/reports/test_report_aggregate_reports_dir.py` | `tests/unit/reports/test_report_aggregate_reports_dir.py` | unit | Unit tests for report aggregation/validation. |
| `tests/unit/reports/test_report_validator_modules.py` | `tests/unit/reports/test_report_validator_modules.py` | unit | Unit tests for report aggregation/validation. |
| `tests/unit/reports/test_reporting.py` | `tests/unit/reports/test_reporting.py` | unit | Unit tests for report aggregation/validation. |

### Unit Tests: Tools → `tests/unit/tools/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/tools/test_custom_tools.py` | `tests/unit/tools/test_custom_tools.py` | unit | Unit tests for tool registry/helpers. |
| `tests/unit/tools/test_tool_error_detection.py` | `tests/unit/tools/test_tool_error_detection.py` | unit | Unit tests for tool registry/helpers. |
| `tests/unit/tools/test_tool_helpers.py` | `tests/unit/tools/test_tool_helpers.py` | unit | Unit tests for tool registry/helpers. |
| `tests/unit/tools/test_tool_registry.py` | `tests/unit/tools/test_tool_registry.py` | unit | Unit tests for tool registry/helpers. |

### Unit Tests: Docs → `tests/unit/docs/`

| Current Path | Target Path | Type | Rationale |
|--------------|-------------|------|-----------|
| `tests/unit/docs/test_docs_audit.py` | `tests/unit/docs/test_docs_audit.py` | unit | Unit tests for docs automation. |
| `tests/unit/docs/test_docs_stale_detection.py` | `tests/unit/docs/test_docs_stale_detection.py` | unit | Unit tests for docs automation. |
| `tests/unit/docs/test_docs_stale_extraction.py` | `tests/unit/docs/test_docs_stale_extraction.py` | unit | Unit tests for docs automation. |
| `tests/unit/docs/test_docs_stale_integration.py` | `tests/unit/docs/test_docs_stale_integration.py` | unit | Unit tests for docs automation. |
| `tests/unit/docs/test_docs_stale_types.py` | `tests/unit/docs/test_docs_stale_types.py` | unit | Unit tests for docs automation. |

## Monolithic File Split Plan (Completed)

> **5 files split** (1000+ lines or 20+ test classes) — completed 2026-01-17

### 1. `test_ci_engine.py` → split into 5 files in `tests/unit/services/ci_engine/`

| New File | Focus |
|----------|-------|
| `tests/unit/services/ci_engine/test_ci_engine_project_detection.py` | Project detection + workdir |
| `tests/unit/services/ci_engine/test_ci_engine_tool_state.py` | Tool state + env toggles |
| `tests/unit/services/ci_engine/test_ci_engine_notifications.py` | Notifications + uploads |
| `tests/unit/services/ci_engine/test_ci_engine_runners.py` | Runner orchestration |
| `tests/unit/services/ci_engine/test_ci_engine_gates.py` | Gate evaluation |

### 2. `test_hub_ci.py` → split into 9 files in `tests/unit/hub_ci/`

| New File | Focus |
|----------|-------|
| `tests/unit/hub_ci/test_hub_ci_helpers.py` | Output helpers |
| `tests/unit/hub_ci/test_hub_ci_linting.py` | Linting tools |
| `tests/unit/hub_ci/test_hub_ci_badges.py` | Badges |
| `tests/unit/hub_ci/test_hub_ci_validation.py` | Validation checks |
| `tests/unit/hub_ci/test_hub_ci_smoke.py` | Smoke checks |
| `tests/unit/hub_ci/test_hub_ci_zizmor_license.py` | Zizmor + license checks |
| `tests/unit/hub_ci/test_hub_ci_mutmut.py` | Mutmut |
| `tests/unit/hub_ci/test_hub_ci_python_tools.py` | Python tools |
| `tests/unit/hub_ci/test_hub_ci_security.py` | Security tools |

### 3. `test_hub_ci_release.py` → split into 4 files in `tests/unit/hub_ci/`

| New File | Focus |
|----------|-------|
| `tests/unit/hub_ci/test_hub_ci_release_analysis.py` | Release analysis |
| `tests/unit/hub_ci/test_hub_ci_release_commands.py` | Release commands |
| `tests/unit/hub_ci/test_hub_ci_release_install.py` | Release installs |
| `tests/unit/hub_ci/test_hub_ci_release_platform.py` | Release platform |

### 4. `test_ci_runner.py` → split into 4 files in `tests/unit/services/ci_runner/`

| New File | Focus |
|----------|-------|
| `tests/unit/services/ci_runner/test_ci_runner_core.py` | Core runner logic |
| `tests/unit/services/ci_runner/test_ci_runner_parsers.py` | Parsers + metrics |
| `tests/unit/services/ci_runner/test_ci_runner_python.py` | Python tools |
| `tests/unit/services/ci_runner/test_ci_runner_java.py` | Java tools |

### 5. `test_docs_stale.py` → split into 4 files in `tests/unit/docs/`

| New File | Focus |
|----------|-------|
| `tests/unit/docs/test_docs_stale_types.py` | Models + types |
| `tests/unit/docs/test_docs_stale_extraction.py` | Extraction logic |
| `tests/unit/docs/test_docs_stale_detection.py` | Detection logic |
| `tests/unit/docs/test_docs_stale_integration.py` | Integration coverage |

---

## Edge Cases / Unclear Placements

| File | Issue | Recommendation |
|------|-------|----------------|
| `tests/snapshots/test_summary_commands.py` | Mix of snapshot + unit tests | Keep as snapshot; snapshot tests benefit from isolation |
| `tests/unit/services/test_registry_service_threshold_mapping.py` | 1842 lines but excellent cohesion | **KEEP AS-IS** - all tests verify same feature |
| `tests/unit/services/test_registry_cross_root.py` | 942 lines but excellent cohesion | **KEEP AS-IS** - all tests verify cross-root ops |
| `tests/unit/config/test_config_module.py` | 995 lines, 81 tests, 14 classes | **KEEP AS-IS** - each class tests one function; excellent cohesion |
| `tests/unit/hub_ci/test_hub_ci_security.py` | 854 lines | **KEEP AS-IS** - focused on security tools |
| `tests/unit/hub_ci/test_hub_ci_python_tools.py` | 834 lines | **KEEP AS-IS** - focused on Python tool execution |

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
| **Unit Tests** | 118 | Isolated function tests |
| **Supporting Files** | 9 | conftest, __init__, snapshots |
| **TOTAL** | **164** | |

| Split Status | Files | Notes |
|--------------|-------|-------|
| Splits completed | 5 | 23 new files |
| Post-split total | 164 | |
