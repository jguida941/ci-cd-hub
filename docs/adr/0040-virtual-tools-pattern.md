# ADR-0040: Virtual Tools Pattern (Hypothesis, jqwik)

**Status**: Accepted  
**Date:** 2026-01-05  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-05  

## Context

Some CI tools don't have standalone runners but instead run through other tools:

- **Hypothesis** (Python): Property-based testing framework that runs via pytest
- **jqwik** (Java): Property-based testing framework that runs via JUnit/Maven
- **codeql** (Both): Static analysis that runs as a GitHub Action, not a local runner
- **docker** (Both): Container builds that may or may not be configured

These "virtual tools" need gate evaluation (did they run? did they pass?) but don't fit the standard runner model where we invoke a binary and capture output.

## Decision

Implement **virtual tools** as gates without dedicated runners:

### 1. Configuration Pattern

```yaml
python:
 tools:
 hypothesis:
 enabled: true
 fail_on_error: true # Toggle to make optional
```

### 2. Gate Evaluation (run-check pattern)

Instead of threshold-based evaluation, virtual tools use a simple run-check:

```python
# In gates.py
hypothesis_cfg = config.get("python", {}).get("tools", {}).get("hypothesis", {}) or {}
fail_hypothesis = bool(hypothesis_cfg.get("fail_on_error", True))

if tools_configured.get("hypothesis") and fail_hypothesis:
 if not tools_ran.get("hypothesis"):
 failures.append("hypothesis did not run")
 elif not tools_success.get("hypothesis"):
 failures.append("hypothesis failed")
```

### 3. Tools Using This Pattern

| Tool | Language | Runs Via | Config Toggle |
|------|----------|----------|---------------|
| hypothesis | Python | pytest | `fail_on_error` |
| jqwik | Java | Maven/JUnit | `fail_on_error` |
| codeql | Both | GitHub Action | `fail_on_error` |
| docker | Both | docker build | `fail_on_error` |

### 4. Report.json Integration

Virtual tools set their status in the same `tools_ran` / `tools_success` dicts:

```json
{
 "tools_configured": { "hypothesis": true },
 "tools_ran": { "hypothesis": true },
 "tools_success": { "hypothesis": true }
}
```

The CI engine or workflow sets these based on:
- pytest markers/collection for hypothesis
- Maven output parsing for jqwik
- Action outcome for codeql
- Exit code for docker build

### 5. Optional vs Required

The `fail_on_error: false` toggle allows teams to:
- Enable the tool for visibility (appears in summary)
- Not fail CI if the tool doesn't run or fails

This is useful for:
- Gradual rollout of property-based testing
- Optional security scans that may not apply to all repos
- Docker builds that are only needed for deployment

## Consequences

### Positive

- **Consistent gate model**: Virtual tools use same pass/fail tracking
- **Configurable enforcement**: `fail_on_error` toggle for gradual adoption
- **No runner complexity**: Don't need to implement runners for tools that run elsewhere
- **Unified reporting**: All tools appear in summary regardless of runner model

### Negative

- **Status detection varies**: Each virtual tool needs custom detection logic
- **Not locally reproducible**: Some tools (codeql) only run in CI
- **Configuration spread**: Tool config may need coordination with pytest/maven config

## Test Coverage

- `tests/test_ci_engine.py::TestVirtualToolGates` - 6 tests covering:
 - Hypothesis not run detection
 - Hypothesis failure detection
 - Hypothesis skip when `fail_on_error: false`
 - jqwik not run detection
 - jqwik failure detection
 - jqwik skip when `fail_on_error: false`

## Files Changed

- `cihub/services/ci_engine/gates.py` - Hypothesis and jqwik gate evaluation
- `config/defaults.yaml` - Default `fail_on_error` settings (future)
- `tests/test_ci_engine.py` - Virtual tool gate tests

## Related ADRs

- ADR-0006: Quality Gates and Thresholds (gate enforcement model)
- ADR-0038: GateSpec Registry (tool definitions)
- ADR-0039: Require Run or Fail Policy (related enforcement pattern)
