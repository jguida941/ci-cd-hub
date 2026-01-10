# ADR-0041: Language Strategy Pattern

**Status**: Accepted
**Date:** 2026-01-05
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-05

## Context

The CI engine had 46+ conditional branches like:

```python
if language == "python":
 # Python-specific tool running
elif language == "java":
 # Java-specific tool running
```

This created several problems:

1. **Adding new languages** required modifying multiple files
2. **Testing** required mocking language-specific branches
3. **Gate evaluation** had duplicate logic for Python and Java
4. **Tool running** logic was scattered across the codebase

## Decision

Extract a **Language Strategy Pattern** that encapsulates all language-specific behavior:

### 1. Package Structure

```
cihub/core/languages/
 __init__.py # Exports get_strategy(), LanguageStrategy
 base.py # LanguageStrategy ABC
 python.py # PythonStrategy
 java.py # JavaStrategy
 registry.py # LANGUAGE_STRATEGIES dict + get_strategy()
```

### 2. LanguageStrategy ABC

```python
class LanguageStrategy(ABC):
 @property
 @abstractmethod
 def name(self) -> str:
 """Language identifier (e.g., 'python', 'java')."""
 ...

 @abstractmethod
 def get_runners(self) -> dict[str, Callable]:
 """Return tool_key -> runner function mapping."""
 ...

 @abstractmethod
 def get_default_tools(self) -> list[str]:
 """Return default enabled tools for this language."""
 ...

 @abstractmethod
 def run_tools(
 self,
 config: dict,
 repo_path: Path,
 workdir: Path,
 output_dir: Path,
 problems: dict,
 **kwargs,
 ) -> dict[str, ToolResult]:
 """Run all enabled tools and return results."""
 ...

 @abstractmethod
 def evaluate_gates(
 self,
 report: dict,
 thresholds: dict,
 tools_configured: dict,
 config: dict,
 ) -> list[str]:
 """Evaluate quality gates and return list of failures."""
 ...

 def detect(self, repo_path: Path) -> float:
 """Return confidence score (0-1) that this language applies."""
 return 0.0

 def get_virtual_tools(self) -> list[str]:
 """Return tools that run via other tools (e.g., hypothesis via pytest)."""
 return []

 def get_docker_config(self, config: dict) -> dict:
 """Extract Docker configuration for this language."""
 return {}
```

### 3. Registry Pattern

```python
# registry.py
from cihub.core.languages.python import PythonStrategy
from cihub.core.languages.java import JavaStrategy

LANGUAGE_STRATEGIES: dict[str, LanguageStrategy] = {
 "python": PythonStrategy(),
 "java": JavaStrategy(),
}

def get_strategy(language: str) -> LanguageStrategy:
 """Get strategy for language, raising ValueError if unknown."""
 strategy = LANGUAGE_STRATEGIES.get(language)
 if not strategy:
 raise ValueError(f"Unsupported language: {language}")
 return strategy
```

### 4. Usage in CI Engine

```python
# In run_ci()
from cihub.core.languages import get_strategy

strategy = get_strategy(language)
tool_results = strategy.run_tools(config, repo_path, workdir, output_dir, problems)
failures = strategy.evaluate_gates(report, thresholds, tools_configured, config)
```

### 5. Gate Evaluation Integration

Each strategy imports from the shared GateSpec registry:

```python
# In PythonStrategy
from cihub.core.gate_specs import PYTHON_THRESHOLDS, PYTHON_TOOLS
```

This ensures gate evaluation and summary rendering stay in sync (per ADR-0038).

## Consequences

### Positive

- **Adding Go/Rust/TypeScript** = one new file + registry entry, zero changes to existing code
- **Single responsibility**: Each strategy owns its language's CI behavior
- **Testable**: Mock `get_strategy()` to inject test doubles
- **No duplicate gate logic**: Each strategy has one `evaluate_gates()` method
- **Type-safe**: ABC enforces method signatures

### Negative

- **More files**: 4 new files in `cihub/core/languages/`
- **Indirection**: Must look up strategy before calling methods
- **Migration effort**: Required refactoring existing conditional branches

## Test Coverage

- `tests/test_language_strategies.py` - Strategy-specific tests
- `tests/test_ci_engine.py` - Integration tests using strategies
- `tests/test_gate_specs.py` - GateSpec registry tests (shared by strategies)

## Files Changed

- `cihub/core/languages/__init__.py` - Package exports
- `cihub/core/languages/base.py` - LanguageStrategy ABC
- `cihub/core/languages/python.py` - PythonStrategy implementation
- `cihub/core/languages/java.py` - JavaStrategy implementation
- `cihub/core/languages/registry.py` - Strategy registry
- `cihub/services/ci_engine/__init__.py` - Uses `get_strategy()`
- `cihub/services/ci_engine/gates.py` - Delegates to strategy.evaluate_gates()

## Related ADRs

- ADR-0038: GateSpec Registry (shared gate definitions)
- ADR-0039: Require Run or Fail Policy (policy enforcement in strategies)
- ADR-0040: Virtual Tools Pattern (strategy.get_virtual_tools())

## Adding a New Language

To add Go support:

```python
# cihub/core/languages/go.py
class GoStrategy(LanguageStrategy):
 @property
 def name(self) -> str:
 return "go"

 def get_runners(self) -> dict[str, Callable]:
 return {
 "go_test": run_go_test,
 "golangci_lint": run_golangci_lint,
 "govulncheck": run_govulncheck,
 }

 def get_default_tools(self) -> list[str]:
 return ["go_test", "golangci_lint"]

 # ... implement remaining methods
```

Then register:

```python
# registry.py
from cihub.core.languages.go import GoStrategy
LANGUAGE_STRATEGIES["go"] = GoStrategy()
```

No other files need modification.
