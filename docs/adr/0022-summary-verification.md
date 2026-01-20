# ADR-0022: Summary Verification Against Reports

**Status**: Accepted  
**Date:** 2025-12-24  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-05  

**Implementation Update (2026-01-05):**
- [x] Contract tests implemented (`tests/test_contract_consistency.py`)
- [x] Self-validation in `cihub ci` catches summary/report drift automatically
- [x] GateSpec registry ensures gates.py and reporting.py use identical definitions
- [x] 8 contract tests verify Python/Java gates match summary rendering

## Context

The hub workflows render human-readable summaries in `$GITHUB_STEP_SUMMARY`. These summaries are built manually from matrix inputs and tool outputs. We observed drift where disabled tools were shown as enabled because of fallback expressions in the summary table. This undermines trust in the summary and makes it hard to verify that reported tool runs match actual artifacts.

We need a repeatable way to validate that the summary matches the actual execution state and generated artifacts.

## Decision

1. **Make summaries authoritative**
 - Remove fallback expressions that coerce false to true in `hub-run-all.yml`.
 - Include `config_basename` and `run_group` in the summary environment table to identify which config produced the output.

2. **Add a validation command**
 - Use `cihub report validate` to compare:
 - Summary table entries vs `report.json` `tools_ran` booleans.
 - Artifact presence vs `tools_ran` for tools that generate reports.
 - Command returns non-zero in `--strict` mode.

3. **Capture summaries and validate in CI**
 - `hub-run-all.yml` stores `$GITHUB_STEP_SUMMARY` at `reports/<config_basename>/summary.md`.
 - `hub-run-all.yml` runs `cihub report validate --strict` per repo against summary + artifacts.

4. **Define the artifact contract**
 - Python tools must upload outputs when enabled:
 - `ruff-report.json`, `black-output.txt`, `isort-output.txt`, `mypy-output.txt`
 - `mutmut-run.log`, `hypothesis-output.txt`, `test-results.xml`

5. **Prevent regressions**
 - Add a test that fails if `matrix.run_* || 'true'` style fallbacks appear in `hub-run-all.yml`.

## Consequences

### Positive
- Summary output reflects real tool toggles.
- A reusable validation script can be run locally or in CI.
- Future summary drift is caught early.
- Summary text is archived alongside per-repo reports.

### Negative
- More artifacts are uploaded and retained per run.

## Usage

```bash
python -m cihub report validate \
 --report report.json \
 --summary summary.md \
 --reports-dir all-reports \
 --strict
```

## Follow-ups

- Consider extending summary capture to reusable workflows if summary validation is needed there.

## Contract Tests (Added 2026-01-05)

`tests/test_contract_consistency.py` ensures gates.py decisions match reporting.py rendering:

```python
# Tests verify both layers agree on:
# - tests_total == 0 → both show failure/NOT RUN
# - Tests pass → both show pass
# - Tests fail → both show failure
# - Tool not run → shows NOT RUN
# - Security vulns → both show failure
```

**Test Coverage:**

| Test | Verifies |
|------|----------|
| `test_python_zero_tests_both_fail` | gates.py fails, summary shows NOT RUN |
| `test_python_tests_pass_both_pass` | gates.py passes, summary shows Passed |
| `test_python_tests_fail_both_fail` | gates.py fails, summary shows Failed |
| `test_python_tool_not_run` | Summary shows NOT RUN for unconfigured tools |
| `test_java_zero_tests_both_fail` | Java gates/summary consistency |
| `test_java_tests_pass_both_pass` | Java gates/summary consistency |
| `test_java_tests_fail_both_fail` | Java gates/summary consistency |
| `test_java_owasp_vulns_both_fail` | Security gates/summary consistency |

## Related

- ADR-0021: Java POM Compatibility and CLI Enforcement
- ADR-0006: Quality Gates and Thresholds (gate definitions)
- ADR-0019: Report Validation Policy (validation modes)
- ADR-0038: GateSpec Registry (single source of truth)
