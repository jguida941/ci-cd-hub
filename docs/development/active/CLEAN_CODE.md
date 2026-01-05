# Clean Code Audit: Scalability & Architecture Improvements

**Date:** 2026-01-04
**Branch:** feat/modularization
**Purpose:** Identify opportunities for polymorphism, encapsulation, and better modular boundaries to make the codebase more scalable.

---

## Executive Summary

| Aspect | Current Score | Key Issue |
|--------|---------------|-----------|
| CLI Layer | 8/10 | Thin adapter ✅, but output handling inconsistent |
| Command Contracts | 6/10 | Loose interface, printing scattered in commands |
| Language Branching | 3/10 | **38+ if-language checks** - major polymorphism opportunity |
| Tool Runners | 7/10 | Unified ToolResult, but manual dispatch logic |
| Config Loading | 9/10 | Excellent - centralized facade with schema validation |
| Context/State | 7/10 | Context exists but `run_ci()` has 9 keyword params |
| Output Formatting | 6/10 | JSON centralized, but commands print directly |
| Env Toggles | 7/10 | Helpers exist, GitHub env reads scattered |

**Biggest Win:** Extract Language Strategies to eliminate 38+ conditional branches.

---

## Part 1: What's Working Well

### 1.1 CLI as Thin Adapter ✅

`cihub/cli.py` follows best practices:

```python
# Lines 108-112: Lazy import pattern - excellent
def cmd_detect(args: argparse.Namespace) -> int | CommandResult:
    from cihub.commands.detect import cmd_detect as handler
    return handler(args)
```

- Parser construction isolated (lines 285-316)
- Exception handling centralized (lines 336-383)
- JSON output formatting in one place (lines 395-402)
- No business logic in CLI layer

### 1.2 Config Loading ✅

Single canonical path with proper facade:

```
cihub/ci_config.py (entry point)
    └── cihub/config/loader/core.py (schema validation + merge)
        └── cihub/config/loader/__init__.py (clean re-exports)
```

All 10+ files that load config use the same path. Deep merge maintains precedence. Schema validation catches errors early.

### 1.3 Tool Runner Interface ✅

`cihub/core/ci_runner/base.py:11-42` defines `ToolResult`:

```python
@dataclass
class ToolResult:
    tool: str
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    artifacts: dict[str, Path]
```

All runners return this. Subprocess calls centralized in `shared.py`.

### 1.4 CommandResult Contract ✅

`cihub/types.py:12-40` provides structured output:

```python
@dataclass
class CommandResult:
    exit_code: int
    summary: str = ""
    problems: list[dict] = field(default_factory=list)
    suggestions: list[dict] = field(default_factory=list)
    files_generated: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
```

CLI layer decides how to render based on `--json` flag.

---

## Part 2: High-Priority Improvements

### 2.1 Extract Language Strategies (CRITICAL)

**Problem:** 38+ `if language == "python"` / `elif language == "java"` checks scattered across codebase.

**Worst offender:** `cihub/services/ci_engine/__init__.py:179-289`
- Two 50+ line branches doing similar work
- Duplicate gate logic (semgrep, trivy checked in both)
- Adding a new language requires touching 10+ files

**Current pattern (anti-pattern):**
```python
# cihub/services/ci_engine/__init__.py:179-289
if language == "python":
    # 50+ lines of Python-specific setup
    runners = PYTHON_RUNNERS
    tool_outputs = _run_python_tools(config, repo_path, workdir, ...)
    gates = _evaluate_python_gates(tool_outputs, config, ...)
elif language == "java":
    # 50+ lines of Java-specific setup
    runners = JAVA_RUNNERS
    tool_outputs = _run_java_tools(config, repo_path, workdir, ...)
    gates = _evaluate_java_gates(tool_outputs, config, ...)
```

**Proposed: Language Strategy Pattern**

```python
# cihub/core/languages/base.py
from abc import ABC, abstractmethod

class LanguageStrategy(ABC):
    """Base class for language-specific CI behavior."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Language identifier (e.g., 'python', 'java')."""

    @abstractmethod
    def get_runners(self) -> dict[str, Callable]:
        """Return tool name -> runner function mapping."""

    @abstractmethod
    def get_default_tools(self) -> list[str]:
        """Return default tool execution order."""

    @abstractmethod
    def run_tools(self, ctx: RunContext) -> dict[str, ToolResult]:
        """Execute all enabled tools, return results."""

    @abstractmethod
    def evaluate_gates(self, results: dict[str, ToolResult], config: dict) -> list[str]:
        """Evaluate quality gates, return list of failed gate names."""

    def detect(self, repo_path: Path) -> float:
        """Return confidence 0.0-1.0 that this language applies."""
        return 0.0
```

```python
# cihub/core/languages/python.py
class PythonStrategy(LanguageStrategy):
    name = "python"

    def get_runners(self) -> dict[str, Callable]:
        return {
            "pytest": run_pytest,
            "ruff": run_ruff,
            "bandit": run_bandit,
            # ...
        }

    def detect(self, repo_path: Path) -> float:
        if (repo_path / "pyproject.toml").exists():
            return 0.9
        if (repo_path / "setup.py").exists():
            return 0.8
        return 0.0
```

```python
# cihub/core/languages/registry.py
LANGUAGE_STRATEGIES: dict[str, LanguageStrategy] = {
    "python": PythonStrategy(),
    "java": JavaStrategy(),
}

def get_strategy(language: str) -> LanguageStrategy:
    if language not in LANGUAGE_STRATEGIES:
        raise ValueError(f"Unsupported language: {language}")
    return LANGUAGE_STRATEGIES[language]

def detect_language(repo_path: Path) -> str:
    """Auto-detect language with highest confidence."""
    best = max(LANGUAGE_STRATEGIES.values(), key=lambda s: s.detect(repo_path))
    if best.detect(repo_path) < 0.5:
        raise ValueError("Could not detect language")
    return best.name
```

```python
# cihub/services/ci_engine/__init__.py - AFTER refactor
def run_ci(language: str, repo_path: Path, ctx: RunContext) -> CIReport:
    strategy = get_strategy(language)

    tool_results = strategy.run_tools(ctx)
    failed_gates = strategy.evaluate_gates(tool_results, ctx.config)

    return build_report(tool_results, failed_gates, ctx)
```

**Files to create:**
- `cihub/core/languages/__init__.py`
- `cihub/core/languages/base.py`
- `cihub/core/languages/python.py`
- `cihub/core/languages/java.py`
- `cihub/core/languages/registry.py`

**Files to modify:**
- `cihub/services/ci_engine/__init__.py` - Remove all if-language branches
- `cihub/services/ci_engine/helpers.py` - Delegate to strategy
- `cihub/services/ci_engine/gates.py` - Move to language strategies
- `cihub/commands/hub_ci/validation.py` - Use strategy.get_default_tools()

**Payoff:**
- Adding Go/Rust/TypeScript = one new file, zero modifications
- Testing: mock strategy, verify calls
- No more duplicate gate logic

---

### 2.2 Centralize Command Output (HIGH)

**Problem:** Commands print directly instead of returning structured results.

**Violations found:**

| File | Line | Issue |
|------|------|-------|
| `commands/detect.py` | 37, 48 | Prints success/error, then returns |
| `commands/run.py` | 70, 80, 88 | `if json_mode: return CommandResult` else `print()` |
| `commands/hub_ci/__init__.py` | 91, 102, 138-140 | 15+ print statements |
| `commands/pom.py` | 157, 163, 169 | Mixed print + CommandResult |
| `commands/secrets.py` | 41, 48, 104 | Prints errors to stderr |

**Current anti-pattern:**
```python
# commands/run.py:67-71
def cmd_run(args):
    # ...
    if json_mode:
        return CommandResult(exit_code=EXIT_FAILURE, summary=message)
    print(message)  # <-- Layer violation!
    return EXIT_FAILURE
```

**Proposed: Commands Always Return CommandResult**

```python
# commands/run.py - AFTER refactor
def cmd_run(args) -> CommandResult:
    # ...
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=message,
        details=traceback_if_debug,  # Human-readable details
    )
```

```python
# cli.py main() - Handle all output
def main(argv: list[str] | None = None) -> int:
    result = args.func(args)

    if isinstance(result, int):
        result = CommandResult(exit_code=result)

    if json_mode:
        print(json.dumps(result.to_payload(...)))
    else:
        # Human output
        if result.summary:
            print(result.summary)
        if result.details:
            print(result.details)
        for problem in result.problems:
            print(f"  {problem['message']}", file=sys.stderr)

    return result.exit_code
```

**Payoff:**
- Guaranteed JSON output works for all commands
- Testing: assert on CommandResult, not stdout capture
- Consistent user experience

---

### 2.3 Extract Tool Adapters (HIGH)

**Problem:** Tool-specific config extraction scattered and duplicated.

**Current pattern:** `cihub/services/ci_engine/python_tools.py:176-198`
```python
def _run_python_tools(config, repo_path, workdir, output_dir, problems, runners):
    for tool in tool_order:
        if tool == "pytest":
            result = runners["pytest"](repo_path, output_dir, fail_fast=config.get("fail_fast"))
        elif tool == "mutmut":
            timeout = config.get("mutmut", {}).get("timeout_minutes", 10)
            result = runners["mutmut"](repo_path, output_dir, timeout_minutes=timeout)
        elif tool == "sbom":
            fmt = config.get("sbom", {}).get("format", "json")
            result = runners["sbom"](repo_path, output_dir, format=fmt)
        elif tool == "docker":
            # 8 lines of config extraction
            result = runners["docker"](repo_path, output_dir, **docker_config)
        # ... 10 more tools
```

**Proposed: Tool Adapter Pattern**

```python
# cihub/core/tools/base.py
@dataclass
class ToolSpec:
    """Everything needed to run a tool."""
    name: str
    command: list[str]
    cwd: Path
    env: dict[str, str]
    timeout_seconds: int
    expected_outputs: list[str]

@dataclass
class ToolAdapter(ABC):
    """Extracts tool-specific config and builds ToolSpec."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def build_spec(self, config: dict, ctx: RunContext) -> ToolSpec:
        """Extract config and build executable spec."""
        pass

    def post_process(self, result: ToolResult) -> ToolResult:
        """Optional: transform result (e.g., parse coverage)."""
        return result
```

```python
# cihub/core/tools/python/pytest.py
class PytestAdapter(ToolAdapter):
    name = "pytest"

    def build_spec(self, config: dict, ctx: RunContext) -> ToolSpec:
        pytest_config = config.get("python", {}).get("pytest", {})
        args = ["pytest", "-v"]

        if pytest_config.get("fail_fast"):
            args.append("-x")
        if pytest_config.get("coverage"):
            args.extend(["--cov", ctx.repo_path])

        return ToolSpec(
            name=self.name,
            command=args,
            cwd=ctx.workdir,
            env=ctx.env,
            timeout_seconds=pytest_config.get("timeout", 300),
            expected_outputs=["pytest.xml", "coverage.xml"],
        )
```

```python
# cihub/core/tools/registry.py
PYTHON_ADAPTERS = [
    PytestAdapter(),
    RuffAdapter(),
    BanditAdapter(),
    # ...
]

def run_tools(adapters: list[ToolAdapter], config: dict, ctx: RunContext) -> dict[str, ToolResult]:
    results = {}
    for adapter in adapters:
        if not is_tool_enabled(adapter.name, config):
            continue
        spec = adapter.build_spec(config, ctx)
        result = execute_spec(spec)  # Centralized subprocess handling
        result = adapter.post_process(result)
        results[adapter.name] = result
    return results
```

**Payoff:**
- Adding new tool = one adapter class
- Config extraction tested in isolation
- Subprocess calls fully centralized

---
### 2.4 Consolidate `_tool_enabled()` (HIGH)

**Problem:** `_tool_enabled()` (or variants) exists in five places (`cihub/config/loader/core.py`, `cihub/services/ci_engine/helpers.py`, `cihub/commands/report/helpers.py`, `cihub/commands/run.py`, `cihub/commands/config_outputs.py`). Any bug fix or semantic change must be replicated everywhere.

**Plan:**
- Create `cihub/config/tools.py` with a single `is_tool_enabled(config: dict, tool: str, language: str | None = None)` helper that handles bool/dict entries, default language scopes, and reserved toggles.
- Update all callers to import the shared helper.
- Add focused tests (e.g., `tests/test_config_tools.py`) covering booleans, dicts with `enabled`, disabled defaults, and language overrides.

**Benefit:** One source of truth for tool toggles, simpler reasoning about flags, easier to extend to new languages.

---
### 2.5 Expand CI Engine Tests (HIGH)

**Problem:** `tests/test_services_ci.py` currently covers only two scenarios. Most language-specific flows and gate evaluations are untested, making refactors risky.

**Plan:**
- After language strategies land, add parameterized tests that:
  - Mock adapters to simulate different tool outcomes (success/failure).
  - Verify gate evaluation logic for coverage/mutation/security thresholds.
  - Exercise env overrides (`CIHUB_RUN_*`, `CIHUB_WRITE_GITHUB_SUMMARY`, etc.).
  - Cover both Python and Java strategies (and future languages).

**Benefit:** Confidence when changing runners/gates; easier to catch regressions.

---
### 2.6 Gate Evaluation Refactor (MEDIUM)

**Problem:** `_evaluate_python_gates` and `_evaluate_java_gates` duplicate long `if` chains for coverage/mutation/security thresholds.

**Plan:**
- Define declarative gate specs (e.g., `Gate(name="coverage", metric="coverage", threshold_key="coverage_min")`).
- Each language strategy supplies its gate list, and a shared evaluator applies the specs.
- Pass actual metrics + thresholds into the evaluator to produce failure details consistently.

**Benefit:** Removing duplicated logic, easier to add/remove gates, and more readable failure reasons.

---

## Part 3: Medium-Priority Improvements

### 3.1 Centralize GitHub Environment Access

**Problem:** 17 files with direct `os.environ.get("GITHUB_*")` calls.

**Scattered in:**
- `services/ci_engine/helpers.py:22` - GITHUB_REPOSITORY
- `services/ci_engine/gates.py:26,31-33` - Multiple GITHUB_* reads
- `commands/hub_ci/__init__.py:63,78,104` - Direct os.environ.get()

**Proposed:**
```python
# cihub/utils/github.py
@dataclass
class GitHubContext:
    """GitHub Actions environment context."""
    repository: str | None
    ref: str | None
    sha: str | None
    run_id: str | None
    run_number: str | None
    actor: str | None
    event_name: str | None
    workspace: Path | None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "GitHubContext":
        env = env or os.environ
        return cls(
            repository=env.get("GITHUB_REPOSITORY"),
            ref=env.get("GITHUB_REF"),
            sha=env.get("GITHUB_SHA"),
            run_id=env.get("GITHUB_RUN_ID"),
            run_number=env.get("GITHUB_RUN_NUMBER"),
            actor=env.get("GITHUB_ACTOR"),
            event_name=env.get("GITHUB_EVENT_NAME"),
            workspace=Path(env["GITHUB_WORKSPACE"]) if "GITHUB_WORKSPACE" in env else None,
        )

    @property
    def is_ci(self) -> bool:
        return self.run_id is not None

    @property
    def owner_repo(self) -> tuple[str, str] | None:
        if self.repository and "/" in self.repository:
            return tuple(self.repository.split("/", 1))
        return None
```

### 3.2 Consolidate RunCI Parameters

**Problem:** `run_ci()` has 9 keyword parameters.

**Current:** `cihub/services/ci_engine/__init__.py:126-139`
```python
def run_ci(
    *,
    output_dir: Path,
    report_path: Path,
    summary_path: Path,
    workdir: Path,
    install_deps: bool,
    correlation_id: str,
    no_summary: bool,
    write_github_summary: bool,
    config_from_hub: dict | None,
    env: Mapping[str, str] | None,
) -> int:
```

**Proposed:**
```python
@dataclass
class RunOptions:
    """Options for CI execution."""
    output_dir: Path
    report_path: Path
    summary_path: Path
    workdir: Path
    install_deps: bool = True
    correlation_id: str = ""
    no_summary: bool = False
    write_github_summary: bool = False
    config_from_hub: dict | None = None
    env: Mapping[str, str] | None = None

def run_ci(options: RunOptions) -> int:
    # ...
```

### 3.3 Tighten CommandResult Contract

**Problem:** All fields optional, commands populate inconsistently.

**Proposed: Define required fields per command category:**

```python
# cihub/types.py
class CommandCategory(Enum):
    CHECK = "check"      # Must have: problems
    GENERATE = "generate"  # Must have: files_generated or files_modified
    REPORT = "report"    # Must have: data
    ACTION = "action"    # Must have: summary

@dataclass
class CommandResult:
    exit_code: int
    category: CommandCategory
    summary: str  # Now required
    # ... rest same

    def __post_init__(self):
        if self.category == CommandCategory.CHECK and not self.problems:
            warnings.warn("CHECK commands should populate problems list")
```

---

## Part 4: Low-Priority / Future Improvements

### 4.1 Output Renderer Abstraction

Separate rendering from logic entirely:

```python
class OutputRenderer(ABC):
    @abstractmethod
    def render(self, result: CommandResult) -> str:
        pass

class HumanRenderer(OutputRenderer):
    def render(self, result: CommandResult) -> str:
        lines = [result.summary]
        for problem in result.problems:
            lines.append(f"  - {problem['message']}")
        return "\n".join(lines)

class JsonRenderer(OutputRenderer):
    def render(self, result: CommandResult) -> str:
        return json.dumps(result.to_payload(), indent=2)

class AiRenderer(OutputRenderer):
    def render(self, result: CommandResult) -> str:
        # Markdown format for LLM consumption
        ...
```

### 4.2 Filesystem/Git Abstractions for Testing

```python
# cihub/utils/filesystem.py
class FileSystem(ABC):
    @abstractmethod
    def read_text(self, path: Path) -> str: ...
    @abstractmethod
    def write_text(self, path: Path, content: str) -> None: ...
    @abstractmethod
    def exists(self, path: Path) -> bool: ...

class RealFileSystem(FileSystem):
    def read_text(self, path: Path) -> str:
        return path.read_text()
    # ...

class MemoryFileSystem(FileSystem):
    """For testing without touching disk."""
    def __init__(self):
        self._files: dict[Path, str] = {}
    # ...
```

---

## Part 5: Anti-Patterns to Eliminate

### 5.1 CLI Re-exporting Helpers ⚠️

`cihub/cli.py:13-61` re-exports 30+ functions for backward compatibility.

**Issue:** Creates dependency on CLI from other modules.

**Mitigation:** Keep re-exports but add deprecation warnings. Eventually remove.

### 5.2 Mixed Return Types

Some commands return `int`, others `CommandResult`.

**Issue:** CLI must handle both, complicates testing.

**Solution:** Migrate all commands to `CommandResult`. CLI converts `int` to `CommandResult` during transition.

### 5.3 Special-Case Handling

`cihub/services/ci_engine/python_tools.py:183-188`:
```python
if tool == "codeql":
    # Special handling for CodeQL
    ...
```

**Issue:** Special cases scattered, hard to find.

**Solution:** Move to tool adapters where special handling is explicit and documented.

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Current Sprint)
- [ ] Create `cihub/core/languages/` structure
- [ ] Extract `PythonStrategy` and `JavaStrategy`
- [ ] Update `run_ci()` to use strategy pattern
- [ ] Add tests for strategy selection

### Phase 2: Output Consistency
- [ ] Audit all commands for direct printing
- [ ] Convert to `CommandResult` returns
- [ ] Centralize output in `cli.py`
- [ ] Add renderer abstraction

### Phase 3: Tool Adapters
- [ ] Create `cihub/core/tools/` structure
- [ ] Extract Python tool adapters
- [ ] Extract Java tool adapters
- [ ] Centralize subprocess execution

### Phase 4: Polish
- [ ] Centralize GitHub env access
- [ ] Consolidate `run_ci()` parameters
- [ ] Add deprecation warnings to CLI re-exports
- [ ] Documentation updates

---

## Appendix: Files by Refactoring Priority

### Must Touch (High Impact)
| File | Lines | Issue |
|------|-------|-------|
| `services/ci_engine/__init__.py` | 179-289 | Language branching |
| `services/ci_engine/python_tools.py` | 176-198 | Tool dispatch |
| `services/ci_engine/java_tools.py` | 80-103 | Tool dispatch |
| `services/ci_engine/helpers.py` | 104-134 | Duplicate gate config |

### Should Touch (Medium Impact)
| File | Lines | Issue |
|------|-------|-------|
| `commands/run.py` | 67-89 | Direct printing |
| `commands/detect.py` | 37-48 | Direct printing |
| `commands/hub_ci/__init__.py` | 91-140 | 15+ print statements |
| `services/ci_engine/gates.py` | 26-33 | Scattered env reads |

### Nice to Touch (Low Impact)
| File | Lines | Issue |
|------|-------|-------|
| `cli.py` | 13-61 | Re-exports (keep for now) |
| `types.py` | 12-40 | Loose contract |
| `utils/env.py` | - | Add GitHub context |

---

## Summary

The codebase has strong foundations (config loading, CLI adapter pattern, ToolResult interface) but suffers from **excessive language branching** that makes it hard to extend.

**One refactor** - extracting Language Strategies - would eliminate 38+ conditionals and make adding new languages trivial.

The other improvements (output consistency, tool adapters, GitHub context) are incremental and can be done file-by-file without breaking changes.