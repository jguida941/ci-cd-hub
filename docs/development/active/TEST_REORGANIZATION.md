# Test Suite Reorganization Plan

**Date:** 2026-01-05
**Status:** PLANNED (10-12 day blockers)
**Priority:** **#3** (See [MASTER_PLAN.md](../MASTER_PLAN.md#active-design-docs---priority-order))
**Depends On:** CLEAN_CODE.md Part 2.2 (CommandResult migration) + REGISTRY_AUDIT Part 6 (wizard integration)
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
| `registry_service.py` | [ ] None | **CRITICAL** (see REGISTRY_AUDIT Part 15) |

**Note:** Registry service testing is comprehensively covered in REGISTRY_AUDIT_AND_PLAN.md Part 15 with 6 test categories and ~1,350 lines of test code proposed.

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
 note: "Legacy code - see CLEAN_CODE.md"
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
- [ ] Add `cihub hub-ci thresholds` command (read/write to config/defaults.yaml)
- [ ] Add per-module override support to config/defaults.yaml schema
- [ ] Create `scripts/update_test_metrics.py` (reads targets from config/defaults.yaml)
- [ ] Create `scripts/generate_test_readme.py`
- [ ] Create `scripts/check_test_drift.py`
- [ ] Add to CI workflow (hub-production-ci.yml)

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

- `CLEAN_CODE.md` - Code quality improvements (complete first)
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
| `cihub hub-ci thresholds` CLI command | [ ] NOT IMPLEMENTED | 2-3 days |
| Schema per-module overrides | [ ] BLOCKED by `additionalProperties: false` | 1 day |
| 3 automation scripts | [ ] NOT IMPLEMENTED | 4-5 days |
| Only 2/15 thresholds in CI outputs | WARNING: INCOMPLETE | 2 days |

**Estimated effort before Phase 1: ~10-12 days**

### Test File Coverage Gap

- **78 test files** currently in flat `tests/` directory
- **43 files (55%)** map to proposed categories
- **35 files (45%)** need NEW categories added

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
- [ ] Implement `cihub hub-ci thresholds` command
- [ ] Update schema for per-module overrides
- [ ] Create comprehensive file mapping (all 78 files → new homes)
- [ ] Split large monolithic test files (120+ tests)
- [ ] Register pytest markers in pyproject.toml
