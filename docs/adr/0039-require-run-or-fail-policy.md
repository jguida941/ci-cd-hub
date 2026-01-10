# ADR-0039: Require Run or Fail Policy

**Status**: Accepted
**Date:** 2026-01-05
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-05

## Context

When a tool is configured (`enabled: true`) but doesn't run (`tools_ran[tool] = false`), the previous behavior was to show "NOT RUN" in the summary but **not fail CI**. This created a silent failure mode:

1. Security tool crashes → No security scan runs → CI passes
2. Test tool misconfigured → No tests run → CI passes
3. Network issue → Dependency scan skips → CI passes

For critical tools (tests, security scanners), this is unacceptable. We need a policy that:
- Fails CI when critical tools don't run
- Allows optional tools (mutation testing) to skip without failing
- Is configurable per-tool and globally

## Decision

Implement `require_run_or_fail` policy at two levels:

### 1. Global Default

```yaml
# config/defaults.yaml
gates:
 require_run_or_fail: true # Global default
```

### 2. Per-Tool Override

```yaml
# config/defaults.yaml or repo config
python:
 tools:
 pytest:
 enabled: true
 require_run_or_fail: true # Tests MUST run
 mutmut:
 enabled: true
 require_run_or_fail: false # Mutation testing optional
```

### 3. Tool Defaults (in defaults.yaml)

```yaml
gates:
 tool_defaults:
 # Critical tools - must run
 pytest: { require_run_or_fail: true }
 bandit: { require_run_or_fail: true }
 pip_audit: { require_run_or_fail: true }
 owasp: { require_run_or_fail: true }
 trivy: { require_run_or_fail: true }
 codeql: { require_run_or_fail: true }
 jacoco: { require_run_or_fail: true }
 checkstyle: { require_run_or_fail: true }
 spotbugs: { require_run_or_fail: true }
 ruff: { require_run_or_fail: true }

 # Optional tools - can skip
 mutmut: { require_run_or_fail: false }
 pitest: { require_run_or_fail: false }
 docker: { require_run_or_fail: false }
 semgrep: { require_run_or_fail: false }
 sbom: { require_run_or_fail: false }
 mypy: { require_run_or_fail: false }
 black: { require_run_or_fail: false }
 isort: { require_run_or_fail: false }
 pmd: { require_run_or_fail: false }
```

### 4. Enforcement Logic

```python
# In gates.py
def _tool_requires_run_or_fail(tool_key: str, config: dict) -> bool:
 """Check if tool requires run-or-fail policy."""
 # 1. Per-tool setting takes precedence
 # 2. Fall back to global default
 # 3. Fall back to tool_defaults
 ...

def _check_require_run_or_fail(
 tool_key: str,
 tools_configured: dict,
 tools_ran: dict,
 config: dict,
) -> str | None:
 """Check if tool violates require_run_or_fail. Returns failure message or None."""
 if not tools_configured.get(tool_key):
 return None # Not configured, no requirement
 if tools_ran.get(tool_key):
 return None # Ran successfully
 if not _tool_requires_run_or_fail(tool_key, config):
 return None # Not required to run
 return f"{tool_key} is required but did not run"
```

### 5. Summary Rendering

```python
# In reporting.py
if not tools_ran.get(tool_key):
 if tools_require_run.get(tool_key):
 status = "NOT RUN " # Hard failure
 else:
 status = "NOT RUN" # Soft skip
```

### 6. Report Schema

```json
{
 "tools_require_run": {
 "pytest": true,
 "bandit": true,
 "mutmut": false
 }
}
```

This allows artifact-first decisions without reloading config.

## Consequences

### Positive

- **Critical tools can't silently skip**: Tests, security scans must run
- **Configurable per-org**: Organizations can adjust defaults
- **Clear UI distinction**: shows hard failures vs soft skips
- **Artifact-first**: `tools_require_run` in report.json enables offline decisions

### Negative

- **More config complexity**: Another setting to understand
- **Potential CI breakage**: Repos with broken tools will start failing
- **Migration burden**: Existing repos may need config updates

## Test Coverage

- `tests/test_ci_engine.py::TestRequireRunOrFail` - 10 tests covering:
 - Tool required and runs → pass
 - Tool required but doesn't run → fail
 - Tool not required and doesn't run → pass
 - Per-tool override takes precedence
 - Global default fallback
 - Python and Java gate evaluation

## Migration Path

1. Add `require_run_or_fail` settings to `config/defaults.yaml`
2. Update JSON schema for per-tool `require_run_or_fail` property
3. Deploy to fixture repos first (canary)
4. Monitor for unexpected failures
5. Document in AGENTS.md

## Related ADRs

- ADR-0006: Quality Gates and Thresholds (gate enforcement)
- ADR-0038: GateSpec Registry (tool key definitions)
- ADR-0019: Report Validation Policy (validation modes)

## Files Changed

- `config/defaults.yaml` - Policy defaults
- `schema/ci-hub-config.schema.json` - Schema update
- `cihub/services/ci_engine/gates.py` - Enforcement logic
- `cihub/core/reporting.py` - Summary rendering ( annotation)
- `cihub/core/ci_report.py` - `tools_require_run` in report
- `tests/test_ci_engine.py` - Policy tests
