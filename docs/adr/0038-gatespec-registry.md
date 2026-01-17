# ADR-0038: GateSpec Registry (Single Source of Truth)

**Status**: Accepted  
**Date:** 2026-01-05  
**Developer:** Justin Guida  
**Last Reviewed:** 2026-01-05  

## Context

The quality gate system had two independent implementations:

1. **`cihub/services/ci_engine/gates.py`** - Evaluates gates for CI pass/fail decisions
2. **`cihub/core/reporting.py`** - Renders gate status in markdown summaries

These could drift out of sync. Example scenarios:
- `gates.py` adds a new threshold check, but `reporting.py` doesn't render it
- `reporting.py` shows a tool as "Passed" while `gates.py` would fail it
- Different threshold keys or tool names between the two modules

This violated the DRY principle and made contract testing difficult.

## Decision

Create a **GateSpec Registry** (`cihub/core/gate_specs.py`) as the single source of truth for:

1. **Threshold definitions** - What metrics have thresholds, how they're compared
2. **Tool definitions** - What tools exist, their categories and labels
3. **Evaluation logic** - Data-driven threshold evaluation

### 1. ThresholdSpec Dataclass

```python
@dataclass
class ThresholdSpec:
 """Specification for a threshold-based quality gate."""
 label: str # Display name (e.g., "Code Coverage")
 key: str # Config key (e.g., "coverage_min")
 unit: str # Display unit (e.g., "%")
 comparator: str # "ge" (>=) or "le" (<=)
 metric_key: str # Report metric key (e.g., "coverage")
 failure_template: str # Message template for failures
```

### 2. ToolSpec Dataclass

```python
@dataclass
class ToolSpec:
 """Specification for a tool-based quality gate."""
 category: str # "testing", "security", "lint", "build"
 label: str # Display name (e.g., "Unit Tests")
 key: str # Tool key (e.g., "pytest")
```

### 3. Language-Specific Registries

```python
PYTHON_THRESHOLDS: list[ThresholdSpec] = [
 ThresholdSpec("Code Coverage", "coverage_min", "%", "ge", "coverage", ...),
 ThresholdSpec("Max Ruff Errors", "max_ruff_errors", "", "le", "ruff_errors", ...),
 # ... more thresholds
]

PYTHON_TOOLS: list[ToolSpec] = [
 ToolSpec("testing", "Unit Tests", "pytest"),
 ToolSpec("security", "Bandit", "bandit"),
 # ... more tools
]

PYTHON_TOOL_KEYS = frozenset(t.key for t in PYTHON_TOOLS)
```

### 4. Helper Functions

```python
def threshold_rows(language: str) -> list[ThresholdSpec]:
 """Get threshold specs for a language."""

def tool_rows(language: str) -> list[ToolSpec]:
 """Get tool specs for a language."""

def get_tool_keys(language: str) -> frozenset[str]:
 """Get tool keys for require_run_or_fail evaluation."""

def evaluate_threshold(spec: ThresholdSpec, value: float, threshold: float) -> bool:
 """Evaluate a threshold spec. Returns True if passed."""
```

### 5. Usage in gates.py

```python
from cihub.core.gate_specs import get_tool_keys

# In require_run_or_fail loop:
for tool_key in get_tool_keys(language):
 if _tool_requires_run_or_fail(tool_key, merged_config):
 # Check if tool ran...
```

### 6. Usage in reporting.py

```python
from cihub.core.gate_specs import tool_rows, threshold_rows

# In build_quality_gates():
for spec in tool_rows(language):
 # Render tool status row...

for spec in threshold_rows(language):
 # Render threshold row...
```

## Consequences

### Positive

- **Single source of truth**: Gate definitions exist in one place
- **Contract testable**: Same specs used by both modules
- **Type-safe**: Dataclasses with clear fields
- **Extensible**: Add new tools/thresholds by adding to registries
- **DRY**: No duplicate tool lists or threshold logic

### Negative

- **New module to maintain**: `cihub/core/gate_specs.py`
- **Migration required**: Existing code had to be refactored
- **Learning curve**: Developers must understand the registry pattern

## Test Coverage

- `tests/test_gate_specs.py` - 35 tests covering:
 - Registry consistency (Python and Java specs)
 - Threshold evaluation logic
 - Tool key extraction
 - Helper function behavior

## Related ADRs

- ADR-0006: Quality Gates and Thresholds (threshold definitions)
- ADR-0019: Report Validation Policy (validation integration)
- ADR-0022: Summary Verification (contract testing)

## Files Changed

- `cihub/core/gate_specs.py` - New registry module
- `cihub/services/ci_engine/gates.py` - Uses `get_tool_keys()`
- `cihub/core/reporting.py` - Uses `tool_rows()`, `threshold_rows()`
- `cihub/reporting.py` - Backward-compatible facade exports
- `tests/test_gate_specs.py` - Registry tests
