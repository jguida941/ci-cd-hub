# ADR-0042: CommandResult Pattern for CLI Output

**Status**: Accepted
**Date:** 2026-01-05
**Developer:** Justin Guida
**Last Reviewed:** 2026-01-05

## Context

CLI commands had inconsistent output patterns:

```python
# Pattern 1: Print and return int
def cmd_foo(args):
 print("Result: OK")
 return 0

# Pattern 2: Return CommandResult only in JSON mode
def cmd_bar(args):
 if args.json:
 return CommandResult(exit_code=0, summary="OK")
 print("Result: OK")
 return 0

# Pattern 3: Mixed print + return
def cmd_baz(args):
 print("Starting...")
 result = do_work()
 print(f"Done: {result}")
 return CommandResult(exit_code=0, summary=str(result))
```

This created problems:
1. **Testing difficulty**: Had to capture stdout instead of asserting on return values
2. **JSON mode inconsistency**: Some commands supported `--json`, others didn't
3. **Programmatic usage**: Hard to use commands from other code
4. **Error handling**: Exit codes scattered, no structured error data

## Decision

Standardize all commands to return `CommandResult`:

### 1. CommandResult Structure

```python
@dataclass
class CommandResult:
 exit_code: int
 summary: str
 data: dict | None = None
 artifacts: dict[str, str] | None = None
 problems: list[dict] | None = None
```

### 2. Helper Functions

```python
# cihub/commands/hub_ci/__init__.py
def result_ok(summary: str, *, data=None, problems=None) -> CommandResult:
 """Create successful CommandResult."""
 return CommandResult(
 exit_code=EXIT_SUCCESS,
 summary=summary,
 data=data,
 problems=problems,
 )

def result_fail(summary: str, *, problems=None, data=None) -> CommandResult:
 """Create failed CommandResult with auto-generated problem."""
 if problems is None:
 problems = [{"severity": "error", "message": summary}]
 return CommandResult(
 exit_code=EXIT_FAILURE,
 summary=summary,
 data=data,
 problems=problems,
 )
```

### 3. Command Pattern

```python
def cmd_example(args: argparse.Namespace) -> int | CommandResult:
 """Example command following the pattern."""
 json_mode = getattr(args, "json", False)

 try:
 result = do_work()

 if json_mode:
 return result_ok(
 summary=f"Processed {result.count} items",
 data={"count": result.count, "items": result.items},
 )

 # Human-readable output
 print(f"Processed {result.count} items")
 for item in result.items:
 print(f" - {item}")
 return EXIT_SUCCESS

 except Exception as e:
 if json_mode:
 return result_fail(f"Failed: {e}")
 print(f"Error: {e}")
 return EXIT_FAILURE
```

### 4. CLI Router Handling

The CLI router handles both return types:

```python
# In main CLI
result = command_func(args)
if isinstance(result, CommandResult):
 if args.json:
 print(json.dumps(result.to_dict(), indent=2))
 sys.exit(result.exit_code)
else:
 sys.exit(result)
```

### 5. Migration Scope

All 46 hub-ci functions migrated:
- `cmd_detect`, `cmd_run`, `cmd_badge`, `cmd_release`, etc.
- Security tools: `cmd_bandit`, `cmd_trivy`, `cmd_owasp`, etc.
- Java tools: `cmd_checkstyle`, `cmd_spotbugs`, `cmd_jacoco`, etc.
- Python tools: `cmd_pytest`, `cmd_ruff`, `cmd_mypy`, etc.

## Consequences

### Positive

- **Testable**: Assert on `result.exit_code`, `result.data` instead of stdout
- **Consistent JSON**: All commands support `--json` uniformly
- **Structured errors**: `problems` list provides machine-readable errors
- **Composable**: Commands can call other commands and inspect results
- **Artifacts tracking**: Commands can report what files they created

### Negative

- **Verbose**: Simple commands need more boilerplate
- **Dual paths**: Still need print() for human-readable output
- **Migration effort**: Required updating 46 functions

## Test Coverage

- All command tests updated to use `isinstance(result, CommandResult)`
- JSON output tests verify `result.data` structure
- Error tests verify `result.problems` contains expected errors

## Files Changed

- `cihub/commands/hub_ci/__init__.py` - Added helpers
- `cihub/commands/hub_ci/*.py` - All subcommand files migrated
- `cihub/commands/*.py` - Other command modules
- `tests/test_hub_ci.py` - Updated assertions
- `tests/test_commands_*.py` - Updated assertions

## Related ADRs

- ADR-0029: CLI Exit Code Registry (exit code definitions)
- ADR-0025: CLI Modular Restructure (command organization)
