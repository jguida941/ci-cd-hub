# ADR-0052: fail_on_* Flag Normalization

**Status:** Implemented
**Date:** 2026-01-15
**Supersedes:** None

## Context

The CI/CD Hub schema uses various `fail_on_*` patterns to control whether CI should fail when a tool detects issues. These patterns have evolved organically, resulting in inconsistent naming:

### Boolean Failure Flags
| Pattern | Tools | Meaning |
|---------|-------|---------|
| `fail_on_error` | codeql, docker, ruff, spotbugs | Generic tool error |
| `fail_on_findings` | semgrep | SAST findings detected |
| `fail_on_violation` | checkstyle, pmd | Style violations |
| `fail_on_format_issues` | black | Formatting issues |
| `fail_on_issues` | isort | Import order issues |
| `fail_on_vuln` | pip_audit | Vulnerabilities found |
| `fail_on_high/medium/low` | bandit | Severity-level failures |
| `fail_on_critical/high` | trivy | Severity-level failures |
| `fail_on_missing_compose` | docker | Missing file condition |

### Numeric Thresholds
| Pattern | Tools | Meaning |
|---------|-------|---------|
| `fail_on_cvss` | owasp, trivy | CVSS score threshold (0-10) |

### Problems

1. **Inconsistent naming**: Developers must remember different patterns for each tool
2. **Scattered defaults**: Default values were defined in multiple places (schema, defaults.yaml, fallbacks.py, gates.py)
3. **No canonical API**: Code accessing these values used ad-hoc `.get()` calls with hardcoded defaults
4. **Alignment risk**: Schema defaults could drift from code defaults without detection

## Decision

Introduce a normalization layer for `fail_on_*` flags with:

1. **Canonical helper functions** in `cihub/config/normalize.py`:
   - `get_fail_on_flag()`: Access boolean fail_on_* flags consistently
   - `get_fail_on_cvss()`: Access CVSS threshold values consistently

2. **Centralized defaults** aligned with schema:
   - `_FAIL_ON_KEY_MAP`: Maps tool → canonical flag key
   - `_FAIL_ON_DEFAULTS`: Default values for each flag pattern
   - `_TOOL_FAIL_ON_DEFAULTS`: Tool-specific overrides
   - Property-based tools (hypothesis, jqwik) remain non-configurable and follow test results only

3. **Schema alignment tests** that verify code defaults match schema defaults

## API

```python
from cihub.config import get_fail_on_flag, get_fail_on_cvss

# Boolean flags
fail_on_high = get_fail_on_flag(config, "bandit", "python", "fail_on_high")
fail_on_error = get_fail_on_flag(config, "codeql", "java")  # Uses canonical mapping

# CVSS thresholds
cvss_threshold = get_fail_on_cvss(config, "owasp", "java")  # Returns 7.0 by default
```

## Default Values

All defaults are aligned with schema:

| Tool | Flag | Default | Notes |
|------|------|---------|-------|
| bandit | fail_on_high | `true` | Security findings should fail |
| bandit | fail_on_medium | `false` | Opt-in for stricter gates |
| bandit | fail_on_low | `false` | Opt-in for strictest gates |
| black | fail_on_format_issues | `false` | Formatting is advisory |
| isort | fail_on_issues | `false` | Import order is advisory |
| pip_audit | fail_on_vuln | `true` | Security findings should fail |
| ruff | fail_on_error | `true` | Lint errors should fail |
| trivy | fail_on_critical | `false` | Container scanning opt-in |
| trivy | fail_on_high | `false` | Container scanning opt-in |
| checkstyle | fail_on_violation | `true` | Style violations should fail |
| pmd | fail_on_violation | `false` | PMD is advisory by default |
| spotbugs | fail_on_error | `true` | Bug detection should fail |
| owasp | fail_on_cvss | `7` | CVSS >= 7 (high severity) |
| trivy | fail_on_cvss | `7` | CVSS >= 7 (high severity) |

## Consequences

### Positive
- **Consistent API**: Single way to access fail_on_* values
- **Documented behavior**: ADR and code comments explain the pattern
- **Schema alignment**: Tests catch drift between schema and code defaults
- **Backward compatible**: Existing schema naming preserved

### Negative
- **Learning curve**: Developers should use helpers instead of raw `.get()`
- **Migration needed**: Existing code can be gradually updated to use helpers

### Neutral
- Schema naming remains unchanged (backward compatibility)
- Helpers are additive, not replacing existing schema structure

## Implementation

- **Location**: `cihub/config/normalize.py`
- **Exports**: `cihub/config/__init__.py`
- **Tests**: `tests/test_fail_on_normalization.py` (55 tests)

## References

- [ADR-0038: GateSpec Registry](0038-gatespec-registry.md) - Related threshold infrastructure
- [ADR-0039: require_run_or_fail Policy](0039-require-run-or-fail-policy.md) - Related gate policy
