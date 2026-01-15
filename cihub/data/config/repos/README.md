# Repository Configurations

This directory contains YAML configurations for repositories managed by the CI Hub.

## Configuration Categories

### 1. Fixture Configs (`fixtures-*.yaml`)

**Purpose:** Test scenarios for the CI system itself

**Threshold Pattern:** Intentionally permissive
```yaml
thresholds:
 coverage_min: 50 # Low - fixture code is minimal
 mutation_score_min: 0 # Disabled - not the focus
 max_critical_vulns: 100 # High - fixtures may have old deps
 max_high_vulns: 100 # High - not production code
```

**Why permissive?**
- Fixtures test CI tool execution, not code quality
- Some fixtures intentionally have vulnerabilities for CVE detection tests
- `*-failing` fixtures are designed to trigger gate failures
- `*-passing` fixtures should pass without strict quality requirements

### 2. Canary Configs (`canary-*.yaml`)

**Purpose:** Production baselines for workflow validation

**Threshold Pattern:** Strict
```yaml
thresholds:
 coverage_min: 70 # Production-grade
 mutation_score_min: 70 # Production-grade
 max_critical_vulns: 0 # Zero tolerance
 max_high_vulns: 0 # Zero tolerance
```

**Why strict?**
- Canaries validate real workflow templates
- They represent the quality bar for production repos
- Breaking changes to workflows are caught here first

### 3. Smoke Test Configs (`smoke-test-*.yaml`)

**Purpose:** Fast validation of hub functionality

**Threshold Pattern:** Permissive (like fixtures)
```yaml
thresholds:
 coverage_min: 50
 mutation_score_min: 0
 max_critical_vulns: 100
 max_high_vulns: 100
```

**Why permissive?**
- Smoke tests verify hub commands work, not code quality
- They point to existing repos that may not be under our control
- Must pass reliably for CI system verification

## Tool Configuration Patterns

### Fail-on-Error Settings

For fixtures, many tools have `fail_on_error: false` to prevent false positives:
```yaml
ruff:
 enabled: true
 fail_on_error: false # Report issues but don't fail CI
```

For canaries, tools may be strict but with appropriate thresholds:
```yaml
ruff:
 enabled: true
 fail_on_error: true
 max_errors: 0
```

### Heavy Tools

Some configs enable "heavy" tools (Trivy, CodeQL, OWASP) for comprehensive testing:
- `fixtures-*-heavy.yaml` - Full tool suite
- `canary-*.yaml` - All production tools enabled

## Adding New Configs

1. **For fixtures:** Use permissive thresholds, focus on tool execution
2. **For canaries:** Use strict thresholds, match production requirements
3. **For smoke tests:** Use permissive thresholds, ensure reliable passes

## Audit Notes

Last audited: 2026-01-05

| Config Pattern | Purpose | Thresholds | Status |
|----------------|---------|------------|--------|
| `fixtures-*-passing` | Tool execution tests | Permissive | Intentional |
| `fixtures-*-failing` | Gate failure tests | Permissive | Intentional |
| `canary-*` | Production baseline | Strict | Correct |
| `smoke-test-*` | Hub functionality | Permissive | Intentional |

All permissive thresholds in fixture/smoke configs are intentional design decisions,
not security oversights.
