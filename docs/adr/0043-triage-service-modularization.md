# ADR-0043: Triage Service Modularization

**Status**: Accepted
**Date:** 2026-01-05
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-05

## Context

The triage service (`cihub/services/triage_service.py`) grew to handle multiple concerns:

1. **Data types**: TriageBundle, ToolEvidence, ToolStatus
2. **Evidence building**: Validating tool outputs, building evidence
3. **Detection**: Flaky test patterns, gate changes, test count regression
4. **Bundle generation**: Creating triage.json, priority.json, markdown

A single 800+ line file made it hard to:
- Find specific functionality
- Test components in isolation
- Add new detection algorithms

## Decision

Split into a package with focused modules:

### 1. Package Structure

```
cihub/services/triage/
    __init__.py     # Re-exports public API
    types.py        # Data models (TriageBundle, ToolEvidence, etc.)
    evidence.py     # Evidence building and validation
    detection.py    # Flaky/regression detection algorithms
```

### 2. Module Responsibilities

**types.py** - Data Models
```python
@dataclass
class ToolStatus:
    status: str  # passed, failed, skipped, required_not_run
    reason: str | None = None

@dataclass
class ToolEvidence:
    tool: str
    status: ToolStatus
    metrics: dict | None = None
    artifacts: list[str] | None = None

@dataclass
class TriageBundle:
    triage: dict
    priority: dict
    markdown: str
    history_entry: dict

class MultiTriageResult:
    # Aggregated results from multiple bundles
    ...

# Constants
TRIAGE_SCHEMA_VERSION = "cihub-triage-v2"
SEVERITY_ORDER = ["blocker", "critical", "high", "medium", "low", "info"]
CATEGORY_ORDER = ["security", "test", "gate", "lint", "build", "docs"]
```

**evidence.py** - Evidence Building
```python
def build_tool_evidence(
    report: dict,
    tool_key: str,
    output_dir: Path,
) -> ToolEvidence:
    """Build evidence for a single tool from report data."""
    ...

def validate_artifact_evidence(
    bundle: TriageBundle,
    output_dir: Path,
) -> list[dict]:
    """Validate artifacts exist and are non-empty."""
    ...
```

**detection.py** - Detection Algorithms
```python
def detect_flaky_patterns(
    history_path: Path,
    min_runs: int = 5,
) -> dict[str, Any]:
    """Detect flaky test patterns from triage history."""
    ...

def detect_gate_changes(
    history_path: Path,
    min_runs: int = 2,
) -> dict[str, Any]:
    """Detect gate status changes over time."""
    ...

def detect_test_count_regression(
    history_path: Path,
    current_count: int,
) -> list[dict]:
    """Detect test count drops >10%."""
    ...
```

### 3. Public API (__init__.py)

```python
# Re-export everything for backward compatibility
from .types import (
    ToolStatus, ToolEvidence, TriageBundle, MultiTriageResult,
    TRIAGE_SCHEMA_VERSION, SEVERITY_ORDER, CATEGORY_ORDER, ...
)
from .evidence import build_tool_evidence, validate_artifact_evidence
from .detection import (
    detect_flaky_patterns, detect_gate_changes, detect_test_count_regression
)

# Bundle generation stays in triage_service.py for now
# (will migrate in future commit)
```

### 4. Migration Strategy

Phase 1 (done): Extract types, evidence, detection
Phase 2 (future): Move bundle generation to `generation.py`
Phase 3 (future): Move markdown building to `markdown.py`

## Consequences

### Positive

- **Focused modules**: Each file has one responsibility
- **Easier testing**: Can test detection algorithms in isolation
- **Discoverable**: Clear where to find flaky detection vs evidence building
- **Extensible**: Add new detection algorithms without touching other code

### Negative

- **More files**: 4 files instead of 1
- **Import changes**: Internal imports need updating
- **Partial migration**: Bundle generation still in triage_service.py

## Test Coverage

- `tests/test_triage_service.py` - Integration tests (30 tests)
- Tests import from `cihub.services.triage` package
- Detection algorithms have dedicated test classes

## Files Changed

- `cihub/services/triage/__init__.py` - Package exports
- `cihub/services/triage/types.py` - Data models
- `cihub/services/triage/evidence.py` - Evidence building
- `cihub/services/triage/detection.py` - Detection algorithms
- `cihub/services/triage_service.py` - Imports from package

## Related ADRs

- ADR-0035: Registry, Triage, and LLM Bundle (triage design)
- ADR-0040: Virtual Tools Pattern (evidence for virtual tools)
