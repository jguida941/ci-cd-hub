# ADR-0046: OutputRenderer Pattern

**Status**: Accepted
**Date:** 2026-01-06
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-06
**Updated:** 2026-01-06 (Added AIRenderer with registry pattern)

## Context

CLI commands need to produce output in multiple formats:
- **Human-readable**: Formatted text with colors, tables, progress indicators
- **JSON**: Machine-parseable structured data for automation and AI tools
- **AI prompt pack**: Markdown formatted for LLM consumption with context and instructions

Before this pattern, commands handled output inconsistently:

```python
# Pattern A: Conditional printing (verbose, error-prone)
def cmd_foo(args):
 result = do_work()
 if args.json:
 print(json.dumps({"result": result}))
 else:
 print(f"Result: {result}")
 print(" Details:")
 for item in result.items:
 print(f" - {item}")
 return 0

# Pattern B: Print-then-return (breaks JSON mode)
def cmd_bar(args):
 print("Starting...") # This pollutes JSON output!
 result = do_work()
 return CommandResult(data={"result": result})
```

This led to:
1. **JSON pollution**: Human messages mixed into JSON output
2. **Testing difficulty**: Had to capture stdout instead of asserting on data
3. **Inconsistent formatting**: Each command reimplemented table/list rendering

## Decision

Implement the **OutputRenderer Pattern** with separation of concerns:

### 1. Package Structure

```
cihub/output/
 __init__.py # Exports get_renderer()
 renderers.py # OutputRenderer ABC + implementations
 formatters.py # Table/list/progress formatters
```

### 2. OutputRenderer ABC

```python
from abc import ABC, abstractmethod
from cihub.types import CommandResult

class OutputRenderer(ABC):
 """Abstract base class for rendering CommandResult to output."""

 @abstractmethod
 def render(self, result: CommandResult) -> None:
 """Render a CommandResult to the appropriate output format."""
 ...

 @abstractmethod
 def render_error(self, message: str, details: str | None = None) -> None:
 """Render an error message."""
 ...
```

### 3. Implementations

```python
class HumanRenderer(OutputRenderer):
 """Renders CommandResult as human-readable text."""

 def render(self, result: CommandResult) -> None:
 print(result.summary)
 if result.problems:
 for problem in result.problems:
 severity = problem.get("severity", "info")
 message = problem.get("message", "")
 print(f" [{severity}] {message}")
 if result.data:
 # Pretty-print relevant data fields
 ...

class JsonRenderer(OutputRenderer):
 """Renders CommandResult as JSON to stdout."""

 def render(self, result: CommandResult) -> None:
 import json
 output = {
 "exit_code": result.exit_code,
 "summary": result.summary,
 "data": result.data or {},
 "problems": result.problems or [],
 }
 print(json.dumps(output, indent=2))

class AIRenderer(OutputRenderer):
 """Renders CommandResult as AI-consumable markdown prompt pack."""

 def render(self, result: CommandResult, command: str, duration_ms: int) -> str:
 from .ai_formatters import get_ai_formatter
 formatter = get_ai_formatter(command)
 if formatter:
 # Convention: report data under "*_report" keys
 report_key = self._find_report_key(result.data)
 if report_key:
 return formatter(result.data[report_key])
 return self._default_format(result, command)
```

### 4. AI Formatter Registry Pattern

Commands that support `--ai` mode register their formatters in a central registry:

```python
# cihub/output/ai_formatters.py
_AI_FORMATTERS: dict[str, tuple[str, str]] = {
 # (module_path, function_name) - lazy imports to avoid circular deps
 "docs stale": ("cihub.commands.docs_stale.output", "format_ai_output"),
}

def get_ai_formatter(command: str) -> AIFormatter | None:
 """Get AI formatter for a command, with lazy import."""
 if command not in _AI_FORMATTERS:
 return None
 module_path, func_name = _AI_FORMATTERS[command]
 module = importlib.import_module(module_path)
 return getattr(module, func_name)
```

**Convention:** Commands pass report data under keys ending with `_report` (e.g., `stale_report`).
The AIRenderer looks for these keys and passes the data to the registered formatter.

### 6. Factory Function

```python
def get_renderer(json_mode: bool = False, ai_mode: bool = False) -> OutputRenderer:
 """Get appropriate renderer based on output mode.

 Priority: AI > JSON > Human (most specific mode wins)
 """
 if ai_mode:
 return AIRenderer()
 if json_mode:
 return JsonRenderer()
 return HumanRenderer()
```

### 7. CLI Integration

```python
# cihub/cli.py
def main():
 args = parse_args()
 json_mode = getattr(args, "json", False)
 ai_mode = getattr(args, "ai", False)

 result = handler(args)

 if isinstance(result, CommandResult):
 renderer = get_renderer(json_mode=json_mode, ai_mode=ai_mode)
 output = renderer.render(result, command, duration_ms)
 print(output)
 sys.exit(result.exit_code)
 else:
 # Legacy int return
 sys.exit(result)
```

### 6. Command Pattern

Commands now focus solely on business logic:

```python
def cmd_detect(args: argparse.Namespace) -> CommandResult:
 """Detect project language - pure business logic, no output concerns."""
 language = detect_language(Path(args.path))

 if not language:
 return CommandResult(
 exit_code=EXIT_FAILURE,
 summary="No supported language detected",
 problems=[{"severity": "error", "message": "Could not detect language"}],
 )

 return CommandResult(
 exit_code=EXIT_SUCCESS,
 summary=f"Detected {language} project",
 data={"language": language, "path": str(args.path)},
 )
```

## Consequences

### Positive

- **Clean separation**: Commands produce data, renderers format it
- **Consistent JSON**: All commands produce identical JSON structure
- **Testable**: Assert on CommandResult.data, not stdout
- **Extensible**: Easy to add new renderers (YAML, XML, etc.)
- **AI-friendly**: JSON output is directly consumable by LLMs

### Negative

- **New abstraction**: Developers must understand the pattern
- **Migration effort**: Existing commands needed refactoring
- **Indirection**: Output flows through renderer layer

## Test Coverage

- `tests/test_output_renderers.py` - 35 tests covering:
 - HumanRenderer formatting
 - JsonRenderer structure
 - Error rendering
 - Edge cases (empty data, nested problems)

## Files Changed

- `cihub/output/__init__.py` - Package exports
- `cihub/output/renderers.py` - Renderer implementations
- `cihub/cli.py` - CLI integration (lines 394-400)
- `tests/test_output_renderers.py` - Renderer tests

## Related ADRs

- ADR-0042: CommandResult Pattern (data contract)
- ADR-0029: CLI Exit Codes (exit code handling)
- ADR-0025: CLI Modular Restructure (command organization)

## Migration Status

As of 2026-01-06:
- [x] OutputRenderer infrastructure complete
- [x] 47 commands return CommandResult
- [x] Only 7 intentional print() calls remain (progress indicators)
- [x] Contract enforcement test prevents regression
