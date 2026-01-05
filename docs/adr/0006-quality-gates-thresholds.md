# ADR-0006: Quality Gates and Thresholds

**Status**: Accepted
**Date:** 2025-12-14
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-05

**Implementation Update (2026-01-05):**
- ✅ CVSS enforcement fully implemented (parser + gate evaluation)
- ✅ `require_run_or_fail` policy implemented (tools that must run can fail CI)
- ✅ GateSpec registry created (single source of truth for gates.py + reporting.py)
- ✅ Self-validation after `cihub ci` catches summary/report contradictions
- ✅ Contract tests ensure gate evaluation matches summary rendering  

## Context

CI pipelines need pass/fail criteria. Questions:
- What metrics should have thresholds?
- Should thresholds be global or per-repo configurable?
- What happens when thresholds are violated?
- How do we handle security vulnerabilities?

## Decision

**Threshold Types:**

| Metric | Default | Configurable | Enforcement |
|--------|---------|--------------|-------------|
| Coverage (min %) | 70 | Yes | Per-tool plugin (JaCoCo/pytest-cov) |
| Mutation score (min %) | 70 | Yes | Warning only (not blocking) |
| OWASP CVSS (fail >=) | 7 | Yes | Workflow step + plugin fails build |
| Trivy CVSS (fail >=) | 7 | Yes | Workflow step (Trivy-specific gate) |
| Critical vulns (max) | 0 | Yes | Workflow step enforces count |
| High vulns (max) | 0 | Yes | Workflow step enforces count |

**Configuration Hierarchy:**
1. Per-tool settings (e.g., `java.tools.jacoco.min_coverage: 80`)
2. Threshold presets via `thresholds_profile` (coverage-gate, security, compliance)
3. Global thresholds (e.g., `thresholds.coverage_min: 70`)
4. Hub defaults (`config/defaults.yaml`)

Per-tool settings take precedence over global thresholds.
Explicit `thresholds.*` values override the preset. If `thresholds.trivy_cvss_fail`
is not set, it falls back to `thresholds.owasp_cvss_fail` for backward compatibility.

**Enforcement Behavior:**

1. **Coverage:**
   - JaCoCo: `check` goal with `<minimum>` rule
   - pytest-cov: `--cov-fail-under` flag
   - Enforced at build time, fails the job

2. **Mutation score:**
   - PITest: `mutationThreshold` in pom.xml
   - mutmut: reported but not blocking
   - Currently warning only in hub (too slow for PR checks)

3. **OWASP (Java):**
   - `failBuildOnCVSS` parameter in Maven plugin
   - Workflow step also enforces CVSS threshold
   - Fails if any dependency has CVSS >= threshold

4. **Trivy (Python/Java):**
   - Workflow step enforces CVSS threshold (Trivy-specific)
   - Uses `thresholds.trivy_cvss_fail` (falls back to `thresholds.owasp_cvss_fail`)
   - Fails if any vulnerability has CVSS >= threshold

5. **Vulnerability counts:**
   - Config keys: `thresholds.max_critical_vulns`, `thresholds.max_high_vulns`
   - **Enforced** in workflow "Enforce Thresholds" steps
   - Counts critical/high vulns from OWASP, pip-audit, Trivy reports

## Alternatives Considered

1. **Hard-fail on all thresholds:** Rejected. Mutation testing too slow for PR checks.
2. **No thresholds (advisory only):** Rejected. Quality would degrade over time.
3. **Aggregate thresholds:** Rejected. Per ADR-0004, per-repo metrics are primary.
4. **External quality gate (SonarQube):** Rejected for MVP. Adds infrastructure.

## Consequences

**Positive:**
- Consistent quality standards across repos
- Configurable per-repo for different needs
- Fast feedback via build-time enforcement
- Mutation score as advisory prevents slow PR builds

**Negative:**
- Different tools enforce differently (some warn, some fail)
- Repos must configure plugins to respect thresholds
- CVSS parsing depends on JSON report format consistency

## Implementation Notes

- Threshold config: `config/defaults.yaml` thresholds section
- JaCoCo enforcement: requires `check` goal in pom.xml
- OWASP enforcement: `failBuildOnCVSS` parameter
- Mutation score: reported in step summary, not blocking

**Resolved Limitations (2026-01-05):**

1. ~~**No quality gate summary job:**~~ → **RESOLVED**
   - Self-validation runs after `cihub ci` and fails on contradictions
   - Contract tests (`tests/test_contract_consistency.py`) verify gates.py matches reporting.py

2. ~~**CVSS parsing is format-dependent:**~~ → **RESOLVED**
   - `_parse_dependency_check()` extracts `owasp_max_cvss` from OWASP JSON
   - `run_trivy()` extracts `trivy_max_cvss` from Trivy JSON
   - Gates enforce CVSS thresholds (`owasp_cvss_fail`, `trivy_cvss_fail`)

**New Capabilities (2026-01-05):**

1. **GateSpec Registry** (`cihub/core/gate_specs.py`):
   - Single source of truth for gate definitions
   - `ThresholdSpec` and `ToolSpec` dataclasses
   - Used by both `gates.py` and `reporting.py`
   - See ADR-0038 for details

2. **require_run_or_fail Policy**:
   - Tools that must run will fail CI if they don't
   - Defaults: pytest, bandit, pip_audit, owasp, trivy, codeql, jacoco = `true`
   - Summary shows "X NOT RUN" for hard failures
   - See ADR-0039 for details

3. **Virtual Tools Pattern**:
   - Hypothesis (Python) and jqwik (Java) gates for property-based testing
   - Run via pytest/Maven, not standalone runners
   - Use `fail_on_error` toggle for optional enforcement
   - See ADR-0040 for details

4. **Flaky Test Detection** (implemented):
   - `cihub triage --detect-flaky` analyzes history.jsonl for state changes
   - Flakiness score based on pass/fail alternation frequency

## Future Work

- Add threshold trend tracking (is coverage improving?)
- Add Semgrep/Trivy findings to unified vuln counts
