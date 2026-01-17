# CIHub CLI Architecture Improvements
> **Superseded by:** [MASTER_PLAN.md](../MASTER_PLAN.md)

> **WARNING: SUPERSEDED:** This document has been consolidated into `docs/development/archive/CLEAN_CODE.md`.
> Architecture improvements are now tracked in the active CLEAN_CODE.md design doc.
>
> **Status:** Archived
> **Date:** 2026-01-03
> **Based on**: Comprehensive codebase audit + industry best practices

This document identifies architectural improvements to make the CIHub CLI more **scalable**, **maintainable**, and aligned with **enterprise design patterns**.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Issues](#current-architecture-issues)
3. [Industry Best Practices](#industry-best-practices)
4. [Detailed Improvement Plan](#detailed-improvement-plan)
5. [Extraction Schedule](#extraction-schedule)
6. [New Abstractions to Create](#new-abstractions-to-create)
7. [Code Duplication to Eliminate](#code-duplication-to-eliminate)
8. [Testing Strategy](#testing-strategy)
9. [Migration Safety](#migration-safety)

---

## Executive Summary

### Key Problems Identified

| Issue | Severity | Impact |
|-------|----------|--------|
| **cli.py has 628 lines** with business logic | HIGH | CLI should be ~100 lines (thin entry point) |
| **12 functions in cli.py** that belong elsewhere | HIGH | Violates separation of concerns |
| **Config loading duplicated** in 4+ places | HIGH | Inconsistent behavior, hard to maintain |
| **No shared helpers** for common patterns | MEDIUM | Code duplication across commands |
| **Missing service layer** for several features | MEDIUM | Commands doing business logic directly |
| **No polymorphism** for tool runners | LOW | Harder to extend, test, and maintain |

### Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ CLI Layer │
│ cli.py: Parser + main() + thin cmd_* wrappers (~100 lines) │
└─────────────────────────────────────────────────────────────┘
 │
 ▼
┌─────────────────────────────────────────────────────────────┐
│ Commands Layer │
│ commands/*.py: Parse args, call services, format output │
│ (No business logic - only orchestration + output) │
└─────────────────────────────────────────────────────────────┘
 │
 ▼
┌─────────────────────────────────────────────────────────────┐
│ Services Layer │
│ services/*.py: Business logic, workflows, orchestration │
│ (Pure functions, testable, no I/O concerns) │
└─────────────────────────────────────────────────────────────┘
 │
 ▼
┌─────────────────────────────────────────────────────────────┐
│ Core Layer │
│ core/*.py: Domain entities, tool runners, report types │
│ (Low-level, stable abstractions) │
└─────────────────────────────────────────────────────────────┘
 │
 ▼
┌─────────────────────────────────────────────────────────────┐
│ Utils Layer │
│ utils/*.py: Pure utilities (I/O, HTTP, env, git, etc.) │
│ (No business logic, reusable across all layers) │
└─────────────────────────────────────────────────────────────┘
```

---

## Current Architecture Issues

### 1. cli.py Business Logic Violations

**cli.py should only contain:**
- `build_parser()` - Parser construction
- `main()` - Entry point
- `cmd_*` wrappers - Thin delegators to commands
- Re-exports for backward compatibility

**Currently contains (WRONG):**

| Function | Lines | Problem | Move To |
|----------|-------|---------|---------|
| `write_text()` | 64-71 | I/O utility | `utils/io.py` |
| `detect_language()` | 74-94 | Business logic | `services/detection.py` |
| `load_effective_config()` | 97-107 | Config business logic | `config/loader/core.py` |
| `safe_urlopen()` | 121-125 | HTTP utility | `utils/http.py` |
| `is_debug_enabled()` | 128-129 | Env utility | `utils/env.py` |
| `build_repo_config()` | 152-180 | Config building | `services/config_builder.py` |
| `render_caller_workflow()` | 183-195 | Template rendering | `services/templates.py` |
| `resolve_language()` | 198-205 | Business logic | `services/detection.py` |
| `get_connected_repos()` | 326-360 | Repo discovery | `services/discovery.py` |
| `get_repo_entries()` | 363-401 | Repo discovery | `services/discovery.py` |
| `render_dispatch_workflow()` | 404-414 | Template rendering | `services/templates.py` |
| `delete_remote_file()` | 422-435 | GitHub API | `utils/github_api.py` |

### 2. Missing Service Layer Components

| Missing Service | Currently Handled By | Functions Needed |
|-----------------|---------------------|------------------|
| `services/detection.py` | cli.py | `detect_language()`, `resolve_language()` |
| `services/templates.py` | cli.py, commands/templates.py | `render_workflow()`, `render_dispatch_workflow()` |
| `services/config_builder.py` | cli.py | `build_repo_config()`, `build_effective_config()` |
| `services/init.py` | commands/init.py (too much) | `initialize_repo()`, `apply_fixes()` |
| `services/check.py` | commands/check.py (583 lines) | `run_checks()`, `install_tools()` |

### 3. Code Duplication

| Pattern | Locations | Should Be |
|---------|-----------|-----------|
| Config loading | `cli.py`, `ci_config.py`, `config/loader/`, `services/configuration.py` | Single `config/loader/core.py::load_effective_config()` |
| Tool enabled check | `run.py`, `config_outputs.py`, services | Single `utils/config.py::is_tool_enabled()` |
| Nested dict access | `config_outputs.py` (3 functions) | Single `utils/dict_utils.py` module |
| JSON mode handling | Every command | Single `utils/output.py::format_output()` |
| Error handling | Every command | Decorator or base handler |

### 4. God Files (Excessive Responsibility)

| File | Lines | Issues |
|------|-------|--------|
| `commands/hub_ci/release.py` | 824 | CI runner + release logic mixed |
| `cli.py` | 628 | Entry point + config + discovery + templates |
| `cli_parsers/hub_ci.py` | 627 | Should split by subcommand group |
| `core/reporting.py` | 584 | All report formats in one file |
| `commands/check.py` | 583 | Orchestration + tool install + steps |

---

## Industry Best Practices

Based on research from leading sources:

### Service Layer Pattern

> "The Service Layer acts as an intermediate layer between the application interface (e.g., API, UI) and the domain or persistence layers... improving modularity, scalability, and testability."
> - [Enterprise Design Pattern: Service Layer in Python](https://dev.to/ronal_daniellupacamaman/enterprise-design-pattern-implementing-the-service-layer-pattern-in-python-57mh)

**Key principle**: Services coordinate domain objects to perform business operations. Commands should call services, not implement business logic.

### Clean Architecture

> "The objective of Clean Architecture is to separate the main codebase of the application from parts of the code that deal with external libraries and systems."
> - [Clean Architecture in Python](https://www.linkedin.com/pulse/implementation-clean-architecture-python-part-1-cli-watanabe)

**Key principle**: The CLI layer (commands, parsers) should depend on services, which depend on core. Never the reverse.

### Dependency Injection

> "Dependency injection allows for very flexible and easy unit-testing, enabling an architecture where you can change data storing on-the-fly."
> - [Python Design Patterns for Clean Architecture](https://www.glukhov.org/post/2025/11/python-design-patterns-for-clean-architecture/)

**Key principle**: Services should receive dependencies (config, clients) rather than creating them.

### Single Responsibility

> "Each module should have a single, well-defined responsibility. This principle helps create more focused and manageable code."
> - [How to Design Modular Python Projects](https://labex.io/tutorials/python-how-to-design-modular-python-projects-420186)

**Key principle**: A module should have one reason to change. cli.py currently has 12+ reasons.

### Layered Architecture for CLI

> "Layered architecture is appropriate for complex business logic when your application requires clear separation of concerns... when your application needs to handle different types of requests (API, CLI, background jobs) while maintaining consistent business logic."
> - [Best Practices for Structuring a Python CLI Application](https://medium.com/@ernestwinata/best-practices-for-structuring-a-python-cli-application-1bc8f8a57369)

### Command Pattern for Scalability

> "The Command design pattern encapsulates a request as an object, which allows you to parameterize clients with various requests, schedule or queue a request's execution."
> - [Python Command Design Pattern Tutorial](https://arjancodes.com/blog/python-command-design-pattern-tutorial-for-scalable-applications/)

---

## Detailed Improvement Plan

### Phase 1: Extract from cli.py (HIGH Priority)

These changes are safe and provide immediate wins:

#### 1.1 Move `delete_remote_file()` to `utils/github_api.py`

```python
# In utils/github_api.py - add this function
def delete_remote_file(repo: str, path: str, branch: str, sha: str, message: str) -> None:
 """Delete a file from a GitHub repo via the GitHub API."""
 payload = {"message": message, "sha": sha, "branch": branch}
 gh_api_json(f"/repos/{repo}/contents/{path}", method="DELETE", payload=payload)
```

```python
# In cli.py - add re-export
from cihub.utils.github_api import delete_remote_file # noqa: F401
```

#### 1.2 Move `is_debug_enabled()` to `utils/env.py`

```python
# In utils/env.py - add this function
def is_debug_enabled(env: Mapping[str, str] | None = None) -> bool:
 """Check if debug mode is enabled via CIHUB_DEBUG env var."""
 return env_bool("CIHUB_DEBUG", default=False, env=env)
```

#### 1.3 Create `utils/io.py` with `write_text()`

```python
# New file: utils/io.py
from pathlib import Path

def write_text(path: Path, content: str, dry_run: bool, emit: bool = True) -> None:
 """Write text to a file, with dry-run support."""
 if dry_run:
 if emit:
 print(f"# Would write: {path}")
 print(content)
 return
 path.parent.mkdir(parents=True, exist_ok=True)
 path.write_text(content, encoding="utf-8")
```

#### 1.4 Move repo discovery functions to `services/discovery.py`

```python
# In services/discovery.py - add these functions
def get_connected_repos(only_dispatch_enabled: bool = True, language_filter: str | None = None) -> list[str]:
 """Get unique repos from hub config/repos/*.yaml."""
 # ... existing code from cli.py

def get_repo_entries(only_dispatch_enabled: bool = True) -> list[dict[str, str]]:
 """Return repo metadata from config/repos/*.yaml."""
 # ... existing code from cli.py
```

### Phase 2: Create Missing Services (MEDIUM Priority)

#### 2.1 Create `services/detection.py`

```python
# New file: services/detection.py
from pathlib import Path

def detect_language(repo_path: Path) -> tuple[str | None, list[str]]:
 """Detect repository language from file markers."""
 checks = {
 "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
 "python": ["pyproject.toml", "requirements.txt", "setup.py"],
 }
 # ... rest of logic

def resolve_language(repo_path: Path, override: str | None) -> tuple[str, list[str]]:
 """Resolve language with optional override."""
 if override:
 return override, []
 detected, reasons = detect_language(repo_path)
 if not detected:
 reason_text = ", ".join(reasons) if reasons else "no language markers found"
 raise ValueError(f"Unable to detect language ({reason_text}); use --language.")
 return detected, reasons
```

#### 2.2 Create `services/templates.py`

```python
# New file: services/templates.py
from pathlib import Path
from cihub.utils import hub_root

def render_caller_workflow(language: str) -> str:
 """Render a caller workflow for the given language."""
 templates_dir = hub_root() / "templates" / "repo"
 # ... rest of logic

def render_dispatch_workflow(language: str, dispatch_workflow: str) -> str:
 """Render a dispatch workflow."""
 # ... rest of logic
```

#### 2.3 Create `services/config_builder.py`

```python
# New file: services/config_builder.py
from pathlib import Path
from typing import Any
from cihub.config.io import load_yaml_file
from cihub.utils import hub_root

def build_repo_config(language: str, owner: str, name: str, branch: str, subdir: str | None = None) -> dict[str, Any]:
 """Build a repo config from template."""
 template_path = hub_root() / "templates" / "repo" / ".ci-hub.yml"
 # ... rest of logic
```

### Phase 3: Create Shared Helpers (MEDIUM Priority)

#### 3.1 Create `utils/dict_utils.py`

```python
# New file: utils/dict_utils.py
from typing import Any, TypeVar

T = TypeVar("T")

def get_nested(data: dict, *keys: str, default: T = None) -> T:
 """Safely get a nested dictionary value."""
 current = data
 for key in keys:
 if not isinstance(current, dict):
 return default
 current = current.get(key)
 if current is None:
 return default
 return current

def get_str(data: dict, *keys: str, default: str = "") -> str:
 """Get a nested string value."""
 value = get_nested(data, *keys, default=default)
 return str(value) if value is not None else default

def get_int(data: dict, *keys: str, default: int = 0) -> int:
 """Get a nested int value."""
 value = get_nested(data, *keys, default=default)
 try:
 return int(value)
 except (TypeError, ValueError):
 return default

def get_bool(data: dict, *keys: str, default: bool = False) -> bool:
 """Get a nested bool value."""
 value = get_nested(data, *keys, default=default)
 if isinstance(value, bool):
 return value
 if isinstance(value, str):
 return value.lower() in ("true", "1", "yes", "on")
 return default
```

#### 3.2 Create `utils/output.py`

```python
# New file: utils/output.py
import json
import sys
from typing import Any

def is_json_mode(args) -> bool:
 """Check if JSON output mode is enabled."""
 return getattr(args, "json", False)

def format_result(result: Any, json_mode: bool) -> str:
 """Format a result for output."""
 if json_mode:
 return json.dumps(result, indent=2)
 # Human-readable formatting
 return str(result)

def emit_result(result: Any, json_mode: bool) -> None:
 """Emit a result to stdout."""
 print(format_result(result, json_mode))

def emit_error(message: str, json_mode: bool) -> None:
 """Emit an error message."""
 if json_mode:
 print(json.dumps({"error": message}), file=sys.stderr)
 else:
 print(f"Error: {message}", file=sys.stderr)
```

### Phase 4: Add Polymorphism (LOW Priority)

#### 4.1 Create `core/tool_runner.py` Protocol

```python
# New file: core/tool_runner.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

@dataclass
class ToolResult:
 success: bool
 exit_code: int
 stdout: str
 stderr: str
 artifacts: list[Path]

class ToolRunner(Protocol):
 """Protocol for tool runners."""

 @property
 def name(self) -> str:
 """Tool name."""
 ...

 def is_available(self) -> bool:
 """Check if tool is available."""
 ...

 def run(self, workdir: Path, output_dir: Path) -> ToolResult:
 """Run the tool."""
 ...

class BaseToolRunner(ABC):
 """Base class for tool runners with common functionality."""

 @property
 @abstractmethod
 def name(self) -> str:
 pass

 @abstractmethod
 def is_available(self) -> bool:
 pass

 @abstractmethod
 def run(self, workdir: Path, output_dir: Path) -> ToolResult:
 pass

 def _run_subprocess(self, cmd: list[str], workdir: Path) -> tuple[int, str, str]:
 """Common subprocess execution."""
 import subprocess
 result = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
 return result.returncode, result.stdout, result.stderr
```

---

## Extraction Schedule

### Safe Extraction Order (Minimal Risk)

Each step should be:
1. Extracted to new location
2. Re-exported from cli.py for backward compat
3. Tests run to verify
4. Commit

| Order | Function | From | To | Risk |
|-------|----------|------|-----|------|
| 1 | `delete_remote_file` | cli.py:422-435 | utils/github_api.py | LOW |
| 2 | `is_debug_enabled` | cli.py:128-129 | utils/env.py | LOW |
| 3 | `write_text` | cli.py:64-71 | utils/io.py (new) | LOW |
| 4 | `safe_urlopen` | cli.py:121-125 | utils/http.py (new) | LOW |
| 5 | `detect_language` | cli.py:74-94 | services/detection.py (new) | MEDIUM |
| 6 | `resolve_language` | cli.py:198-205 | services/detection.py | MEDIUM |
| 7 | `get_connected_repos` | cli.py:326-360 | services/discovery.py | MEDIUM |
| 8 | `get_repo_entries` | cli.py:363-401 | services/discovery.py | MEDIUM |
| 9 | `build_repo_config` | cli.py:152-180 | services/config_builder.py (new) | MEDIUM |
| 10 | `render_caller_workflow` | cli.py:183-195 | services/templates.py (new) | MEDIUM |
| 11 | `render_dispatch_workflow` | cli.py:404-414 | services/templates.py | MEDIUM |
| 12 | `load_effective_config` | cli.py:97-107 | config/loader/core.py | HIGH |

---

## New Abstractions to Create

### Utils Layer

| Module | Purpose | Functions |
|--------|---------|-----------|
| `utils/io.py` | File I/O helpers | `write_text()`, `read_text()`, `ensure_dir()` |
| `utils/http.py` | HTTP utilities | `safe_urlopen()`, `fetch_json()` |
| `utils/dict_utils.py` | Dict manipulation | `get_nested()`, `get_str()`, `get_int()`, `get_bool()` |
| `utils/output.py` | Output formatting | `is_json_mode()`, `format_result()`, `emit_result()` |

### Services Layer

| Module | Purpose | Functions |
|--------|---------|-----------|
| `services/detection.py` | Language detection | `detect_language()`, `resolve_language()` |
| `services/templates.py` | Template rendering | `render_workflow()`, `render_dispatch_workflow()` |
| `services/config_builder.py` | Config building | `build_repo_config()`, `build_effective_config()` |
| `services/github.py` | GitHub operations | `GitHubClient` class wrapping API calls |

### Core Layer

| Module | Purpose | Types |
|--------|---------|-------|
| `core/tool_runner.py` | Tool abstraction | `ToolRunner` protocol, `BaseToolRunner` ABC |
| `core/reporter.py` | Report abstraction | `Reporter` protocol for different formats |

---

## Code Duplication to Eliminate

### Priority Duplications

1. **Config Loading** - Consolidate to single `load_effective_config()` in `config/loader/core.py`
2. **Tool Enabled Checks** - Create `utils/config.py::is_tool_enabled()`
3. **Nested Dict Access** - Use new `utils/dict_utils.py` helpers everywhere
4. **JSON Mode Handling** - Use new `utils/output.py` helpers in all commands
5. **Error Handling** - Create decorator `@handle_command_errors` for commands

---

## Testing Strategy

### Before Each Extraction

1. Identify all callers: `grep -r "from cihub.cli import <function>"`
2. Ensure test coverage exists for the function
3. Run full test suite: `pytest tests/`

### After Each Extraction

1. Run linters: `ruff check cihub/` and `mypy cihub/`
2. Run tests: `pytest tests/`
3. Run smoke test: `python -m cihub --help`
4. Verify backward compat: existing imports still work

### New Test Files Needed

| Test File | Tests |
|-----------|-------|
| `tests/test_utils_io.py` | `write_text()` |
| `tests/test_utils_dict.py` | `get_nested()`, `get_str()`, etc. |
| `tests/test_services_detection.py` | `detect_language()`, `resolve_language()` |
| `tests/test_services_templates.py` | Template rendering functions |

---

## Migration Safety

### Backward Compatibility Rules

1. **Always re-export** from original location after moving
2. **Never change function signatures** during extraction
3. **One function per commit** for easy rollback
4. **Run CI after each extraction** before proceeding

### Example Safe Migration Pattern

```python
# Step 1: Create new location with function
# utils/io.py
def write_text(path: Path, content: str, dry_run: bool, emit: bool = True) -> None:
 ...

# Step 2: Update cli.py to import and re-export
# cli.py
from cihub.utils.io import write_text # noqa: F401 - re-export for backward compat

# Step 3: Remove old implementation from cli.py (the function body)

# Step 4: Existing code continues to work:
from cihub.cli import write_text # Still works!
```

### Deprecation Strategy (Future)

After all extractions are complete and stable:

1. Add deprecation warnings to cli.py re-exports
2. Update documentation to point to new locations
3. In next major version, remove re-exports

---

## References

- [Enterprise Design Pattern: Service Layer in Python](https://dev.to/ronal_daniellupacamaman/enterprise-design-pattern-implementing-the-service-layer-pattern-in-python-57mh)
- [Clean Architecture in Python](https://www.linkedin.com/pulse/implementation-clean-architecture-python-part-1-cli-watanabe)
- [Python Design Patterns for Clean Architecture](https://www.glukhov.org/post/2025/11/python-design-patterns-for-clean-architecture/)
- [Best Practices for Structuring a Python CLI Application](https://medium.com/@ernestwinata/best-practices-for-structuring-a-python-cli-application-1bc8f8a57369)
- [Python Command Design Pattern Tutorial](https://arjancodes.com/blog/python-command-design-pattern-tutorial-for-scalable-applications/)
- [How to Design Modular Python Projects](https://labex.io/tutorials/python-how-to-design-modular-python-projects-420186)
- [Architecture Patterns with Python](https://www.cosmicpython.com/book/chapter_04_service_layer.html)
- [6 Essential Python Design Patterns for Scalable Architecture](https://dev.to/aaravjoshi/6-essential-python-design-patterns-for-scalable-software-architecture-4h8m)
