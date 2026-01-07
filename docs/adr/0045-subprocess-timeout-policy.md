# ADR-0045: Subprocess Timeout Policy

**Status**: Accepted
**Date:** 2026-01-06
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-06

## Context

The codebase has 33+ subprocess calls across 15+ files without timeout parameters. From the INCONSISTENCY.md audit:

| File                             | Count | Risk                |
|----------------------------------|-------|---------------------|
| `cihub/commands/verify.py`       | 4     | CI job hangs        |
| `cihub/commands/check.py`        | 3     | Local command hangs |
| `cihub/commands/triage.py`       | 5     | API call hangs      |
| `cihub/core/ci_runner/shared.py` | 2     | Build process hangs |
| Various                          | 19+   | Mixed risk          |

**Problem:** Without timeouts, a subprocess can hang indefinitely, causing:
1. CI jobs to stall until GitHub's 6-hour limit kills them
2. Local commands to appear frozen with no feedback
3. Resource exhaustion in automated pipelines

## Decision

Establish a **Subprocess Timeout Policy** with tiered defaults based on operation type:

### 1. Timeout Tiers

| Tier         | Timeout  | Use Case                                  |
|--------------|----------|-------------------------------------------|
| **Quick**    | 30s      | Git config, file checks, simple CLI tools |
| **Network**  | 60-120s  | API calls, downloads, remote operations   |
| **Build**    | 300-600s | Compilation, test suites, full builds     |
| **Extended** | 900s     | Mutation testing, comprehensive scans     |

### 2. Standard Pattern

```python
import subprocess
from cihub.constants import TIMEOUT_QUICK, TIMEOUT_NETWORK, TIMEOUT_BUILD

# Quick operation
result = subprocess.run(
    ["git", "config", "--get", "user.name"],
    capture_output=True,
    text=True,
    timeout=TIMEOUT_QUICK,  # 30s
)

# Network operation
result = subprocess.run(
    ["gh", "api", "/repos/owner/repo"],
    capture_output=True,
    text=True,
    timeout=TIMEOUT_NETWORK,  # 120s
)

# Build operation
result = subprocess.run(
    ["mvn", "package", "-DskipTests"],
    capture_output=True,
    text=True,
    timeout=TIMEOUT_BUILD,  # 600s
)
```

### 3. Exception Handling

```python
try:
    result = subprocess.run(cmd, timeout=TIMEOUT_QUICK, ...)
except subprocess.TimeoutExpired as exc:
    # Log and handle gracefully
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"Command timed out after {TIMEOUT_QUICK}s",
        problems=[{
            "severity": "error",
            "code": "SUBPROCESS_TIMEOUT",
            "message": f"Command '{' '.join(cmd)}' exceeded {TIMEOUT_QUICK}s timeout",
        }],
    )
```

### 4. Constants Module

```python
# cihub/constants.py
TIMEOUT_QUICK = 30      # Quick operations (git config, file checks)
TIMEOUT_NETWORK = 120   # Network/API operations
TIMEOUT_BUILD = 600     # Build/test operations (10 minutes)
TIMEOUT_EXTENDED = 900  # Extended operations (mutation testing)
```

### 5. Migration Priority

From INCONSISTENCY.md audit, prioritize by risk:

**High Priority (Security/Reliability):**
- `ci_runner/shared.py` - Build processes can hang indefinitely
- `triage.py` - API calls to GitHub
- `verify.py` - Remote verification calls

**Medium Priority (UX):**
- `check.py` - Local tool checks
- `templates.py` - Template operations
- `hub_ci/*.py` - CI helper commands

**Low Priority (Rare Paths):**
- `docs.py` - Doc generation
- `secrets.py` - Secret management

## Consequences

### Positive

- **Predictable CI behavior**: Jobs fail fast instead of hanging
- **Better UX**: Users get feedback instead of frozen terminals
- **Debuggable**: Timeout failures include command context
- **Testable**: Can mock timeouts in unit tests

### Negative

- **Migration effort**: 33+ call sites to update
- **Tuning required**: Some operations may need adjusted timeouts
- **New constant imports**: Slight increase in module coupling

## Test Coverage

- Add tests that verify TimeoutExpired is handled gracefully
- Add parameterized tests for different timeout tiers
- Add integration tests with mocked slow commands

## Implementation Notes

1. Create `cihub/constants.py` with timeout constants
2. Update call sites incrementally (high priority first)
3. Add `TimeoutExpired` handling to command error paths
4. Add CI enforcement check for missing timeouts (optional)

## Related ADRs

- ADR-0042: CommandResult Pattern (error reporting format)
- ADR-0029: CLI Exit Codes (exit code for timeouts)

## Related Documentation

- `docs/development/INCONSISTENCY.md` - Full audit of missing timeouts
