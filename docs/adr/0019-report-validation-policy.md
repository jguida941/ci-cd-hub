# ADR-0019: Report Validation Policy

**Status**: Accepted  
**Date:** 2025-12-18  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-05  

**Implementation Update (2026-01-05):**
- [x] `cihub report validate --schema` validates against JSON schema
- [x] `cihub report validate --strict` enforces clean-build invariants
- [x] Wired into `cihub check --audit` and `cihub smoke --full`
- [x] **Self-validation** added to `cihub ci` (runs after report generation)
- [x] `ValidationRules.consistency_only` mode for structural checks without clean-build assumptions
- [x] Schema/consistency errors fail CI in GITHUB_ACTIONS, warn locally

## Context

CI workflows generate `report.json` files containing test results, coverage, and tool metrics. To ensure CI pipelines work correctly:

1. Reports must follow the schema (v2.0)
2. Tools must populate their metrics
3. Passing fixtures must have zero issues
4. Failing fixtures must detect issues

Manual validation is error-prone and repetitive across Python and Java stacks. We need a reusable validation approach with simple, boolean-style parameters.

## Decision

### 1. Reusable Validation Script

Create `scripts/validate_report.sh` that:
- Accepts `--stack python|java` to select the appropriate metrics
- Accepts `--expect-clean` (passing fixture) or `--expect-issues` (failing fixture)
- Validates schema version, test results, coverage, tools_ran, and tool_metrics
- Returns exit code 0 (pass) or 1 (fail)

### 2. Script Interface

```bash
# Passing fixture - strict validation (zero issues)
./scripts/validate_report.sh \
 --report ./report/report.json \
 --stack python \
 --expect-clean

# Failing fixture - must detect issues
./scripts/validate_report.sh \
 --report ./report/report.json \
 --stack java \
 --expect-issues \
 --verbose
```

### 3. Validation Rules

#### Common Checks (Both Modes)

| Check | Requirement |
|-------|-------------|
| `schema_version` | Must be "2.0" |
| `results.tests_passed` | Must be > 0 |
| `tools_ran` | Must be object with tools |
| `tool_metrics.*` | Must be populated (not null) for enabled tools |

#### Clean Mode (`--expect-clean`)

| Check | Requirement |
|-------|-------------|
| `results.tests_failed` | Must be 0 |
| `results.coverage` | Must be >= threshold (default 70%) |
| Lint metrics | Must all be 0 |
| Security metrics | Must all be 0 |

#### Issues Mode (`--expect-issues`)

| Check | Requirement |
|-------|-------------|
| Lint metrics | At least one must be > 0 |
| Coverage | No threshold (informational only) |
| Test failures | Allowed (informational) |

### 4. Stack-Specific Metrics

#### Python Metrics

```bash
# Lint (must be 0 for clean)
ruff_errors, black_issues, isort_issues

# Security (must be 0 for clean)
bandit_high, pip_audit_vulns

# All metrics validated for population
ruff_errors, black_issues, isort_issues,
bandit_high, bandit_medium, pip_audit_vulns,
semgrep_findings, trivy_critical, trivy_high
```

#### Java Metrics

```bash
# Lint (must be 0 for clean)
checkstyle_issues, spotbugs_issues, pmd_violations

# Security (must be 0 for clean)
owasp_critical, owasp_high

# All metrics validated for population
checkstyle_issues, spotbugs_issues, pmd_violations,
owasp_critical, owasp_high, semgrep_findings,
trivy_critical, trivy_high
```

### 5. Usage in Workflows

Replace inline validation blocks with script calls:

```yaml
validate-passing:
 name: "Validate Passing Report"
 runs-on: ubuntu-latest
 needs: ci-passing
 if: always()
 steps:
 - name: Checkout Hub (for scripts)
 uses: actions/checkout@v4
 with:
 repository: jguida941/ci-cd-hub
 ref: main
 path: hub

 - name: Download Report
 uses: actions/download-artifact@v4
 with:
 name: python-passing-ci-report
 path: ./report

 - name: Validate Report
 run: |
 hub/scripts/validate_report.sh \
 --report ./report/report.json \
 --stack python \
 --expect-clean \
 --verbose

validate-failing:
 name: "Validate Failing Report"
 runs-on: ubuntu-latest
 needs: ci-failing
 if: always()
 steps:
 - name: Checkout Hub
 uses: actions/checkout@v4
 with:
 repository: jguida941/ci-cd-hub
 ref: main
 path: hub

 - name: Download Report
 uses: actions/download-artifact@v4
 with:
 name: python-failing-ci-report
 path: ./report

 - name: Validate Report
 run: |
 hub/scripts/validate_report.sh \
 --report ./report/report.json \
 --stack python \
 --expect-issues \
 --verbose
```

### 6. Output Format

Script uses GitHub Actions annotation format for CI integration:

```
========================================
Report Validation: python (clean)
========================================
Report: ./report/report.json
Stack: python
Mode: --expect-clean

--- Schema Version ---
 [PASS] schema_version: 2.0

--- Test Results ---
 [PASS] tests_passed: 15
 [PASS] tests_failed: 0

--- Coverage ---
 [PASS] coverage: 87% (threshold: 70%)

--- Tools Ran ---
 [PASS] tools_ran has 8 tools recorded

--- Tool Metrics (populated check) ---
 [PASS] tool_metrics.ruff_errors: 0
 [PASS] tool_metrics.black_issues: 0
 ...

--- Clean Build Checks (zero issues expected) ---
 Lint checks:
 [PASS] ruff_errors: 0
 [PASS] black_issues: 0
 [PASS] isort_issues: 0
 Security checks:
 [PASS] bandit_high: 0
 [PASS] pip_audit_vulns: 0

========================================
Summary
========================================
Errors: 0
Warnings: 0

Validation PASSED
```

Failures show `::error::` annotations visible in GitHub Actions UI.

### 7. Script Location

```
hub-release/
└── scripts/
 └── validate_report.sh # Reusable validation script
```

Future scripts can follow the same pattern with simple boolean flags.

## Consequences

### Positive

- Single source of truth for validation logic
- Reusable across Python and Java workflows
- Simple boolean interface (--expect-clean/--expect-issues)
- GitHub Actions annotation support for CI visibility
- Easy to extend for new metrics or stacks

### Negative

- Requires checkout of hub repo in fixture workflows
- Script must be kept in sync with report schema changes
- Two sources of validation (ADR documentation + script code)

## Migration Path

1. Add script to hub-release repo
2. Test script locally against existing reports
3. Update fixture workflows to use script
4. Remove inline validation blocks
5. Document in migration plan

## Self-Validation in cihub ci (Added 2026-01-05)

After `cihub ci` writes `report.json` and `summary.md`, it runs self-validation:

```python
# In cihub/services/ci_engine/__init__.py
validation = validate_report(
 report,
 ValidationRules(consistency_only=True, strict=False, validate_schema=False),
 summary_text=summary_text,
 reports_dir=output_dir,
)
```

**Validation Modes:**

| Mode | Purpose | When Used |
|------|---------|-----------|
| `consistency_only=True` | Check summary matches report (no clean-build assumptions) | Self-validation after `cihub ci` |
| `strict=True` | Enforce clean-build invariants (0 lint errors, etc.) | `cihub check --audit` |
| `validate_schema=True` | Validate against JSON schema | `cihub report validate --schema` |

**Error Handling:**

- **In CI (GITHUB_ACTIONS):** Schema failures are errors (fail the job)
- **Locally:** Schema failures are warnings (allow scaffold/dev runs with incomplete data)
- **Always:** Consistency failures (summary contradicts report) fail CI

**Test Coverage:**

- `tests/test_ci_self_validate.py` verifies that summary/report contradictions fail `cihub ci`

## Related ADRs

- ADR-0017: Scanner Tool Defaults (defines metrics)
- ADR-0018: Fixtures Testing Strategy (defines fixture types)
- ADR-0014: Reusable Workflow Migration (overall plan)
- ADR-0022: Summary Verification Against Reports (validation strategy)
- ADR-0006: Quality Gates and Thresholds (gate enforcement)
