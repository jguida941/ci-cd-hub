# Clean Code Audit: Scalability & Architecture Improvements

**Date:** 2026-01-04
**Last Updated:** 2026-01-06 (Security audit fixes: path traversal, race conditions, XML handling)
**Branch:** feat/modularization
**Priority:** 🔴 **#1 - CURRENT** (See [MASTER_PLAN.md](../MASTER_PLAN.md#active-design-docs---priority-order))
**Status:** ~85% complete
**Blocks:** TEST_REORGANIZATION.md, TYPESCRIPT_CLI_DESIGN.md, DOC_AUTOMATION_AUDIT.md
**Purpose:** Identify opportunities for polymorphism, encapsulation, and better modular boundaries to make the codebase more scalable.

> ⚠️ **IMPORTANT:** When ALL phases in this document are complete, perform a full audit of
> `MASTER_PLAN.md` to ensure it accurately reflects the new architecture and code locations.
> Architecture changes in this refactoring affect paths, module boundaries, and patterns
> referenced throughout MASTER_PLAN.md.

---

## Master Checklist (AI Navigation Aid)

Use this checklist to track overall progress. Detailed implementation notes are in the referenced sections.

### Completed ✅

- [x] **Part 1.5:** Triage Package Modularization (Reference Pattern)
- [x] **Part 1.6:** Gate Specs Infrastructure (26 thresholds wired)
- [x] **Part 2.2a:** Hub-CI CommandResult Gap (46 functions migrated)
- [x] **Part 2.4:** Consolidate `_tool_enabled()` (1 canonical + 4 delegates)
- [x] **Part 5.1 Phase 1:** Remove CLI re-export comments (411→366 lines)
- [x] **Part 5.4:** CLI Command Sprawl audit (BY DESIGN - API endpoints)
- [x] **Phase 1:** Foundation (Language strategies extracted)
- [x] **Part 10 Phase T1-T3:** Testing foundation, parameterization, property-based

### High Priority (In Progress) 🔄

- [ ] **Part 2.1:** Extract Language Strategies (46 if-language checks remain)
- [x] **Part 2.2:** Centralize Command Output ✅ **DONE** (45→7 prints, 84% reduction - remaining 7 are intentional helpers/progress)
- [x] **Part 2.7:** Consolidate ToolResult ✅ **DONE** (unified in `cihub/types.py`, re-exported for backward compat)
- [x] **Part 7.1:** CLI Layer Consolidation ✅ **DONE** (common.py factory exists, 7.1.2/7.1.3 done in Part 2.2/5.2)
- [x] **Part 7.2:** Hub-CI Subcommand Helpers ✅ **DONE** (write_github_outputs, run_tool_with_json_report, ensure_executable exist)
- [ ] **Part 7.3:** Utilities Consolidation
- [x] **Part 9.3:** Schema Consolidation ✅ **DONE** (sbom/semgrep → sharedTools, toolStatusMap extracted)

### Medium Priority (Pending) ⏳

- [ ] **Part 2.5:** Expand CI Engine Tests
- [ ] **Part 2.6:** Gate Evaluation Refactor
- [ ] **Part 3.1:** Centralize GitHub Environment Access
- [ ] **Part 3.2:** Consolidate RunCI Parameters
- [ ] **Part 5.1 Phases 2-4:** CLI compat module + deprecation warnings
- [x] **Part 5.2:** Mixed Return Types ✅ **DONE** (all 47 commands → pure CommandResult)
- [ ] **Part 5.3:** Special-Case Handling (move to tool adapters)
- [ ] **Part 7.4:** Core Module Refactoring
- [ ] **Part 7.5:** Config/Schema Consistency
- [ ] **Part 7.6:** Services Layer
- [ ] **Part 9.1:** Scripts & Build System
- [ ] **Part 9.2:** GitHub Workflows Security

### Low Priority / Deferred ⏸️

- [ ] **Part 2.3:** Extract Tool Adapters (DEFERRED)
- [ ] **Part 3.3:** Tighten CommandResult Contract (DEFERRED)
- [ ] **Part 4.1:** Output Renderer Abstraction
- [ ] **Part 4.2:** Filesystem/Git Abstractions for Testing
- [ ] **Part 10 Phase T4:** Integration testing (Ongoing)

### Final Validation 🎯

- [ ] All CI tests pass
- [ ] Mutation testing score maintained
- [ ] `MASTER_PLAN.md` audit for accuracy
- [ ] Documentation reflects new architecture

---

## Audit Update (2026-01-05) - Comprehensive Multi-Agent Audit

**NEW:** Part 7 contains results from 6 parallel audit agents covering CLI, services, core, config, utilities, and hub-ci layers. **50 findings identified, 17 high-priority.**

Multi-agent audit validated this document remains **~85% accurate**. Key updates:

| Finding               | Original      | Updated                                                 | Status           |
|-----------------------|---------------|---------------------------------------------------------|------------------|
| Language branches     | 38+           | **46 found**                                            | ✅ Still accurate |
| gate_specs.py         | Not mentioned | **COMPLETE: 26 thresholds wired to evaluate_threshold** | ✅ Fixed          |
| Print in commands     | "scattered"   | **37 files, 46 hub-ci bare int**                        | ⚠️ Under-scoped  |
| _tool_enabled()       | 5 places      | **COMPLETE: 1 canonical + 4 delegates**                 | ✅ Fixed          |
| Triage modularization | N/A           | **COMPLETED - Reference pattern**                       | 🎉 New example   |

**New Reference Pattern:** `cihub/services/triage/` demonstrates the modularization approach. See Part 1.5 below.

## Code Review Fixes (2026-01-05)

Code review identified 4 issues in recently migrated files. All fixed:

| Issue | File | Fix |
|-------|------|-----|
| Not fully migrated (returned `int \| CommandResult`) | detect.py | Changed to pure `CommandResult` return |
| YAML parse errors not caught | validate.py | Added `yaml.YAMLError` and `ValueError` handling |
| TemporaryDirectory resource leak | smoke.py | Added explicit `cleanup()` call |
| Empty check after GITHUB_OUTPUT write | discover.py | Reordered empty check before write |

**CLI improvement:** `cihub/cli.py` now routes error output to stderr (CLI best practice).

## Security Audit Fixes (2026-01-06)

Comprehensive security audit identified and fixed multiple issues:

| Severity | Issue | File | Fix |
|----------|-------|------|-----|
| **Critical** | Path traversal in config paths | `config/paths.py` | Added `_validate_name()` with traversal blocking |
| High | Race condition in ensure_executable | `hub_ci/__init__.py` | Try/except pattern instead of exists check |
| High | Platform detection hardcoded | `hub_ci/release.py` | Added `_get_platform_suffix()` with proper arch detection |
| High | /dev/null portability | `hub_ci/release.py` | Changed to `os.devnull` for cross-platform |
| High | Exit code magic numbers | `hub_ci/validation.py` | Changed to `EXIT_FAILURE` constant |
| High | Return code not checked | `hub_ci/java_tools.py` | Added return code checks for subprocess calls |
| Medium | XML ParseError not caught | `ci_runner/parsers.py` | Added try/except for `_parse_junit`, `_parse_coverage` |
| Medium | ToolResult serialization gaps | `types.py` | Fixed `to_payload`/`from_payload` type handling |
| Low | Line length violations | Multiple | Fixed >120 char lines |
| Low | Unused imports | Multiple | Removed unused `import os` statements |

**Path traversal protection:** The `_validate_name()` function blocks `..`, `\`, and leading `/` to prevent directory escape. Allows `owner/repo` format with explicit `allow_slash=True` parameter for legitimate use cases.

**Tests added:** 6 new tests for platform detection, ensure_executable race condition handling, and path traversal blocking.

---

## Executive Summary

| Aspect             | Current Score | Key Issue                                                                       |
|--------------------|---------------|---------------------------------------------------------------------------------|
| CLI Layer          | 8/10          | Thin adapter ✅, but output handling inconsistent                                |
| **CLI UX**         | 8/10          | 28 commands ✅ BY DESIGN (API endpoints for TS/GUI - see Part 5.4)              |
| Command Contracts  | 9/10          | ✅ **DONE:** 45→7 prints (84% reduction), remaining 7 are intentional helpers/progress |
| Language Branching | 3/10          | **46 if-language checks** - major polymorphism opportunity                      |
| Tool Runners       | 7/10          | Unified ToolResult, but manual dispatch logic                                   |
| Config Loading     | 9/10          | Excellent - centralized facade with schema validation                           |
| Context/State      | 7/10          | Context exists but `run_ci()` has 9 keyword params                              |
| Output Formatting  | 9/10          | **COMPLETE: All 46 hub-ci functions return CommandResult**                      |
| Env Toggles        | 7/10          | Helpers exist, GitHub env reads scattered                                       |
| **Gate Specs**     | 9/10          | **COMPLETE: 26 threshold checks wired to evaluate_threshold**                   |
| **Triage Package** | 9/10          | **Excellent modularization - reference pattern**                                |

**Biggest Win:** Extract Language Strategies to eliminate 46 conditional branches.

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

### 1.5 Triage Package Modularization ✅ (Reference Pattern)

**Completed:** 2026-01-05

`cihub/services/triage/` demonstrates the recommended modularization approach:

```
cihub/services/triage/           # 711 lines across 4 files
├── __init__.py (68 lines)       # Clean facade/re-exports
├── types.py (135 lines)         # Data models (ToolStatus, ToolEvidence, TriageBundle)
├── evidence.py (339 lines)      # Tool evidence building
└── detection.py (169 lines)     # Flaky test/regression detection
```

**Key characteristics (follow this pattern):**

1. **Clear separation of concerns:** Each module has single responsibility
2. **Clean public API:** Re-exports in `__init__.py` with `__all__`
3. **Backward compatibility:** Re-exports maintain public API from parent module
4. **Focused responsibilities:** Types, evidence, detection in separate files
5. **Migration notes:** Comments indicate remaining functions to migrate

**Strangler Fig Pattern Used:**

```python
# cihub/services/triage_service.py (facade)
"""This module is being modularized into cihub/services/triage/."""

from cihub.services.triage.types import (ToolStatus, ToolEvidence, ...)
from cihub.services.triage.evidence import (build_tool_evidence, ...)
from cihub.services.triage.detection import (detect_flaky_patterns, ...)

# Remaining functions still here until migrated
def generate_triage_bundle(...): ...
def write_triage_bundle(...): ...
```

**Result:** Reduced `triage_service.py` from **1134 lines → 565 lines** (50% reduction).

### 1.6 Gate Specs Infrastructure ✅ COMPLETE

`cihub/core/gate_specs.py` defines declarative gate specifications, now **fully wired** into gates.py.

```python
@dataclass(frozen=True)
class ThresholdSpec:
    label: str          # "Min Coverage"
    key: str            # "coverage_min"
    comparator: Comparator  # GTE/LTE/CVSS
    metric_key: str     # "coverage"
    failure_template: str  # "coverage {value}% < {threshold}%"

PYTHON_THRESHOLDS: tuple[ThresholdSpec, ...] = (...)
JAVA_THRESHOLDS: tuple[ThresholdSpec, ...] = (...)
```

**What's now used:**
- `gates.py` imports `get_tool_keys()`, `evaluate_threshold`, `get_threshold_spec_by_key` ✅
- `reporting.py` imports `threshold_rows`/`tool_rows` for summary rendering ✅
- **NEW:** `_check_threshold()` helper wires 26 threshold checks to `evaluate_threshold` ✅

**Implementation (2026-01-05):**
- Added `_check_threshold()` helper to `gates.py`
- Defined 27 ThresholdSpecs in gate_specs.py (Python: 15, Java: 12)
- Refactored Python gates (14 checks): coverage, mutation, ruff, black, isort, mypy, bandit (high/medium/low), pip_audit, semgrep, trivy (critical/high/cvss)
- Refactored Java gates (12 checks): coverage, mutation, checkstyle, spotbugs, pmd, owasp (critical/high/cvss), trivy (critical/high/cvss), semgrep
- All 155 gate-related tests pass — no behavior changes, consistent failure messages

**Remaining non-threshold gates (state machine checks):**
- CodeQL: ran/success state machine (not a numeric threshold)
- Docker: ran/success state machine (not a numeric threshold)

---

## Part 2: High-Priority Improvements

### 2.1 Extract Language Strategies (CRITICAL)

**Problem:** 46 `if language == "python"` / `elif language == "java"` checks scattered across 20 files.

**2026-01-05 Audit Update:** Grep found 46 total checks (2 if + 10 elif patterns × distribution).

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
- ✅ `cihub/services/ci_engine/__init__.py` - Uses strategy for tool execution, report building, gate evaluation
- ✅ `cihub/services/ci_engine/helpers.py` - `_apply_force_all_tools()` uses `strategy.get_default_tools()`
- `cihub/services/ci_engine/gates.py` - Gate logic remains, strategies delegate to it (by design)
- `cihub/commands/hub_ci/validation.py` - N/A (file patterns, not tool lists)

**Payoff:**
- Adding Go/Rust/TypeScript = one new file, zero modifications
- Testing: mock strategy, verify calls
- No more duplicate gate logic

---

### 2.2 Centralize Command Output (HIGH) — In Progress

**Problem:** Commands print directly instead of returning structured results.

**2026-01-05 Progress Update:** Significant progress made on migration:
- ~~**37 files**~~ → **~16 files** in `cihub/commands/` contain direct `print()` calls
- ~~**263+ print() calls**~~ → **~65 print() calls** remaining (~198 migrated)
- **46 hub-ci functions** return CommandResult ✅ (complete)
- **13 major command files migrated:** adr.py (16), triage.py (34), secrets.py (32), templates.py (22), pom.py (21), dispatch.py (10), config_cmd.py (9), update.py (8), smoke.py (8), discover.py (8), docs.py (10), new.py (10), init.py (10)
- Contract enforcement test prevents regression on migrated files

**Remaining violations (top offenders):**

| File                          | Print Calls | Issue                   |
|-------------------------------|-------------|-------------------------|
| `commands/validate.py`        | 7           | Validation output       |
| `commands/run.py`             | 6           | CI run output           |
| `commands/scaffold.py`        | 5           | Scaffolding output      |
| `commands/check.py`           | 5           | Check output            |
| `commands/ci.py`              | 4           | CI info output          |
| `commands/preflight.py`       | 3           | Preflight checks        |
| `commands/detect.py`          | 3           | Detection output        |
| `commands/verify.py`          | 2           | Verification output     |
| `commands/config_outputs.py`  | 2           | Config output           |
| `commands/report/` subpkg     | ~8 files    | Various report outputs  |

**Migrated (no longer in allowlist):**
- ~~`commands/pom.py`~~ (21 prints) ✅
- ~~`commands/secrets.py`~~ (32 prints) ✅
- ~~`commands/templates.py`~~ (22 prints) ✅
- ~~`commands/triage.py`~~ (34 prints) ✅
- ~~`commands/adr.py`~~ (16 prints) ✅
- ~~`commands/dispatch.py`~~ (10 prints) ✅
- ~~`commands/config_cmd.py`~~ (9 prints) ✅
- ~~`commands/update.py`~~ (8 prints) ✅
- ~~`commands/docs.py`~~ (10 prints) ✅
- ~~`commands/new.py`~~ (10 prints) ✅
- ~~`commands/init.py`~~ (10 prints) ✅
- ~~`commands/smoke.py`~~ (8 prints) ✅ **NEW 2026-01-05**
- ~~`commands/discover.py`~~ (8 prints) ✅ **NEW 2026-01-05**
- **All hub-ci subcommands** → ✅ **46 functions return CommandResult**

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

### 2.2a Hub-CI CommandResult Gap ✅ COMPLETE

**Problem:** All 46 hub-ci subcommands returned bare `int`, breaking `--json` support.

**2026-01-05 Final Status:** All 46 functions migrated to CommandResult.

**Migration Progress (2026-01-05):**
| File | Functions | Status |
|------|-----------|--------|
| `cihub/commands/hub_ci/validation.py` | 8 functions | ✅ Complete |
| `cihub/commands/hub_ci/security.py` | 6 functions | ✅ Complete |
| `cihub/commands/hub_ci/smoke.py` | 4 functions | ✅ Complete |
| `cihub/commands/hub_ci/python_tools.py` | 3 functions | ✅ Complete |
| `cihub/commands/hub_ci/java_tools.py` | 6 functions | ✅ Complete |
| `cihub/commands/hub_ci/release.py` | 16 functions | ✅ Complete |
| `cihub/commands/hub_ci/badges.py` | 3 functions | ✅ Complete |
| **Total** | **46/46** | **100% done** |

**Implementation Details:**

1. **CommandResult Helpers Added** (`hub_ci/__init__.py`):
```python
def result_ok(summary: str, *, data=None, problems=None) -> CommandResult:
    """Create successful CommandResult - reduces boilerplate."""

def result_fail(summary: str, *, problems=None, data=None) -> CommandResult:
    """Create failed CommandResult - auto-creates problem from summary."""

def run_and_capture(cmd, cwd, *, tool_name="") -> dict:
    """Run command and capture output for structured results."""
```

2. **Router Pattern Works** (`router.py` lines 120-136):
   - Passes through CommandResult directly
   - Wraps legacy int returns for `--json` mode

3. **Strategy Enhancements Added**:
   - `get_allowed_kwargs()` - Filters kwargs to prevent unexpected parameters
   - `get_virtual_tools()` - Documents tools without runners (hypothesis, jqwik, codeql)
   - `get_docker_config()` - Encapsulates language-specific docker config access

**Payoff:**
- Full `--json` support for automation ✅
- Consistent testing via CommandResult assertions ✅
- Triage can consume structured hub-ci results ✅

---

### 2.3 Extract Tool Adapters (DEFERRED)

**Status:** DEFERRED until output purity complete

**Reviewer Feedback (2026-01-05):** "Don't jump to full ToolAdapter objects yet. You already have:
- tool runners
- ToolResult
- config facade
- strategies

You can get 80% of the value with a smaller step first. Only graduate to
ToolSpec/ToolAdapter when you actually have 3+ tools that need special handling."

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
### 2.4 Consolidate `_tool_enabled()` ✅ COMPLETE

**Problem:** `_tool_enabled()` (or variants) existed in five places. Any bug fix or semantic change had to be replicated everywhere.

**Implementation (2026-01-05):**
- Added canonical `tool_enabled(config, tool, language, *, default=False)` to `cihub/config/normalize.py`
- Exported via `cihub/config/__init__.py` for clean imports
- Updated 4 call sites to delegate to canonical function:
  - `cihub/services/ci_engine/helpers.py`
  - `cihub/commands/report/helpers.py`
  - `cihub/commands/config_outputs.py`
  - `cihub/commands/run.py`
- All 1804 tests pass

**Benefit:** One source of truth for tool toggles, simpler reasoning about flags, easier to extend.

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

### 2.7 Consolidate ToolResult ✅ DONE

**Status:** COMPLETE (2026-01-05)

**Problem (SOLVED):** Two incompatible `ToolResult` definitions existed:

| Location | Focus | Fields |
|----------|-------|--------|
| `cihub/core/ci_runner/base.py` | Metrics | tool, ran, success, metrics, artifacts, stdout, stderr |
| `cihub/commands/hub_ci/__init__.py` | Execution | success, returncode, stdout, stderr, json_data, report_path |

**Reviewer Feedback:** "If you end up with two different ToolResult shapes, you'll regret it
when you merge reports or feed AI. Pick one canonical ToolResult type and re-export it where needed."

**Proposed Fix:** Consolidate to single definition in `cihub/types.py`:

```python
@dataclass
class ToolResult:
    """Unified tool execution result."""
    tool: str
    success: bool
    returncode: int
    stdout: str
    stderr: str
    # From metrics-focused definition
    ran: bool = True
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    # From execution-focused definition
    json_data: Any = None
    json_error: str | None = None
    report_path: Path | None = None
```

**Migration (COMPLETED):**
1. ✅ Created canonical `ToolResult` in `cihub/types.py` (11 fields: tool, success, returncode, stdout, stderr, ran, metrics, artifacts, json_data, json_error, report_path)
2. ✅ Updated `core/ci_runner/base.py` to import from `types.py` and re-export
3. ✅ Updated `commands/hub_ci/__init__.py` to import from `types.py` and re-export
4. ✅ Updated `run_tool_with_json_report()` to use unified type with `tool_name` parameter
5. ✅ All 2104 tests pass

**Benefit:** One source of truth, easier report merging, AI-consumable outputs.

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

### 3.3 Tighten CommandResult Contract (DEFERRED)

**Status:** DEFERRED until all commands return pure CommandResult

**Reviewer Feedback (2026-01-05):** "The CommandCategory + required fields idea is fine, but
it's phase-4 polish. If you add strict invariants while files still print or
return ints, you'll slow the migration and create churn."

**Sequencing:** Wait until:
1. All commands return CommandResult (Phase 2 complete)
2. Renderer consumes CommandResult consistently
3. Then add stronger schema/invariants

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

### 5.1 CLI Re-exporting Helpers ⚠️ (Action Plan Added 2026-01-05)

`cihub/cli.py:14-62` re-exports 30+ functions for backward compatibility.

**Issue:** Creates dependency on CLI from other modules.

**Action Plan:**

1. **Phase 1 ✅ COMPLETE (2026-01-05):** Removed 45 lines of explanatory comments from cli.py
   - File reduced from 411 → 366 lines
   - Re-exports still work, just without redundant comments
2. **Phase 2:** Create `cihub/compat.py` module with all re-exports + deprecation warnings
3. **Phase 3:** Update `cli.py` to: `from cihub.compat import *  # noqa`
4. **Phase 4 (v2.0):** Remove compat.py entirely

**Implementation for Phase 2:**

```python
# cihub/compat.py
"""Backward compatibility re-exports.

DEPRECATED: Import from the canonical locations instead.
This module will be removed in v2.0.
"""
import warnings
from typing import Any

# Canonical re-exports
from cihub.types import CommandResult
from cihub.utils import (
    GIT_REMOTE_RE, hub_root, get_git_branch, get_git_remote,
    parse_repo_from_remote, resolve_executable, validate_repo_path,
    validate_subdir, fetch_remote_file, update_remote_file, gh_api_json,
    # Java POM utilities
    get_java_tool_flags, get_xml_namespace, ns_tag, elem_text,
    parse_xml_text, parse_xml_file, parse_pom_plugins, parse_pom_modules,
    parse_pom_dependencies, plugin_matches, dependency_matches,
    collect_java_pom_warnings, collect_java_dependency_warnings,
    load_plugin_snippets, load_dependency_snippets, line_indent,
    indent_block, insert_plugins_into_pom, find_tag_spans,
    insert_dependencies_into_pom,
)
from cihub.services.configuration import load_effective_config
from cihub.services.detection import detect_language, resolve_language
from cihub.services.repo_config import get_connected_repos, get_repo_entries
from cihub.services.templates import (
    build_repo_config, render_caller_workflow, render_dispatch_workflow,
)

_DEPRECATED_EXPORTS = {
    name for name in dir() if not name.startswith('_')
}

def __getattr__(name: str) -> Any:
    if name in _DEPRECATED_EXPORTS:
        warnings.warn(
            f"Importing '{name}' from cihub.cli or cihub.compat is deprecated. "
            f"Import from the canonical module instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return globals().get(name)
    raise AttributeError(f"module 'cihub.compat' has no attribute '{name}'")
```

**Automation Option:** Add pre-commit hook to detect deprecated imports:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-deprecated-imports
      name: Check deprecated cihub.cli imports
      entry: python scripts/check_deprecated_imports.py
      language: python
      types: [python]
```

### 5.2 Mixed Return Types ✅ DONE

**Status:** COMPLETE (2026-01-05)

**Problem (SOLVED):** Some commands returned `int`, others `CommandResult`, requiring CLI to handle both.

**Migration (COMPLETED):**
1. ✅ Audited all 47 commands with `-> int | CommandResult:` return type
2. ✅ Changed all return types to `-> CommandResult:`
3. ✅ Updated `report/__init__.py` summary subcommands to return `CommandResult` instead of `EXIT_SUCCESS`
4. ✅ Updated type annotations in: `hub_ci/validation.py` (8), `hub_ci/release.py` (17), `hub_ci/python_tools.py` (3), `hub_ci/security.py` (6), `hub_ci/smoke.py` (4), `hub_ci/java_tools.py` (6), `hub_ci/router.py` (1), `check.py` (1)
5. ✅ Fixed test assertions expecting `int` → check `result.exit_code` instead
6. ✅ All 2104 tests pass

**Benefit:** CLI now has consistent return types, simpler testing, guaranteed `--json` support.

### 5.3 Special-Case Handling

`cihub/services/ci_engine/python_tools.py:183-188`:
```python
if tool == "codeql":
    # Special handling for CodeQL
    ...
```

**Issue:** Special cases scattered, hard to find.

**Solution:** Move to tool adapters where special handling is explicit and documented.

### 5.4 CLI Command Sprawl ✅ BY DESIGN (Audited 2026-01-05)

**External Review Finding (Gemini Code Review - Grade B+):**

> "This CLI is functional and comprehensive, but it suffers from 'Command Sprawl.' It feels like a Swiss Army Knife where every new blade was bolted onto the handle wherever it fit, rather than being organized into a neat toolbox."

**⚠️ POST-AUDIT UPDATE: The reviewer also identified that this is INTENTIONAL:**

> "These aren't for humans to type; they are RPC endpoints for the future TypeScript UI to call. This explains the obsession with `--json` output and `CommandResult` objects."

**Audit Results (2026-01-05):**

| Dependency | Commands Referenced | Breaking Change Risk |
|------------|--------------------|--------------------|
| `.github/workflows/hub-ci.yml` | `cihub config-outputs` | **CRITICAL** - CI breaks |
| `.github/workflows/hub-production-ci.yml` | 15+ `cihub hub-ci *` commands | **CRITICAL** - CI breaks |
| `TYPESCRIPT_CLI_DESIGN.md:444-451` | `fix-pom`, `fix-deps`, `setup-secrets`, `setup-nvd`, `config-outputs` | **HIGH** - TS CLI design depends on these |
| `PYQT_PLAN.md:47-50` | Same commands | **HIGH** - GUI design depends on these |
| `cihub/commands/init.py:215` | `cihub fix-pom --repo . --apply` | **MEDIUM** - User-facing suggestions |
| `cihub/commands/update.py:146` | `cihub fix-pom --repo . --apply` | **MEDIUM** - User-facing suggestions |
| 40+ documentation files | All command names | **MEDIUM** - Docs need updating |

**Conclusion: DO NOT RESTRUCTURE COMMANDS**

The "Command Sprawl" is an intentional API design choice:
1. Commands are **stable RPC endpoints** for TypeScript CLI and PyQt GUI
2. Commands are **machine-readable** (all support `--json`)
3. Commands are **CI pipeline callable** (used in 3+ workflow files)

**What CAN be improved (Low Risk):**

1. **Phase CLI-1 (Low risk):** Swap `doctor`/`preflight` help text
   - ✅ Safe: Neither is referenced in workflows or UI designs
   - Change: "doctor" → "Check environment readiness"
   - Change: "preflight" → "Alias for doctor (deprecated)"

2. **Phase CLI-2 (Low risk):** Add argparse help groups for better `--help` output
   - ✅ Safe: Only affects `--help` display, not command names
   - Groups: "Daily Use", "Admin/Setup", "Hub Operations"

**What should NOT be changed:**

| Command | Reason |
|---------|--------|
| `setup-secrets`, `setup-nvd` | TypeScript CLI maps `/setup-*` to these |
| `fix-pom`, `fix-deps` | TypeScript CLI maps `/fix-*` to these |
| `config-outputs` | Used in `hub-ci.yml` workflow |
| `hub-ci *` subcommands | Used in 15+ workflow steps |

**Future: When to reconsider**

Re-evaluate command restructuring ONLY when:
1. TypeScript CLI is complete and can handle aliasing
2. All workflows are updated to use new names
3. Major version bump (v2.0) allows breaking changes

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Current Sprint) ✅
- [x] Create `cihub/core/languages/` structure
- [x] Extract `PythonStrategy` and `JavaStrategy` (delegation pattern)
- [x] Update `run_ci()` to use strategy pattern ✅
- [x] Add tests for strategy selection (33 tests)

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
| File                                 | Lines   | Issue                 | Status                               |
|--------------------------------------|---------|-----------------------|--------------------------------------|
| `services/ci_engine/__init__.py`     | 179-289 | Language branching    | ✅ Refactored to use strategy pattern |
| `services/ci_engine/python_tools.py` | 176-198 | Tool dispatch         | Strategy delegates here              |
| `services/ci_engine/java_tools.py`   | 80-103  | Tool dispatch         | Strategy delegates here              |
| `services/ci_engine/helpers.py`      | 104-134 | Duplicate gate config | ✅ Uses strategy.get_default_tools()  |

### Should Touch (Medium Impact)
| File                          | Lines  | Issue                |
|-------------------------------|--------|----------------------|
| `commands/run.py`             | 67-89  | Direct printing      |
| `commands/detect.py`          | 37-48  | Direct printing      |
| `commands/hub_ci/__init__.py` | 91-140 | 15+ print statements |
| `services/ci_engine/gates.py` | 26-33  | Scattered env reads  |

### Nice to Touch (Low Impact)
| File           | Lines | Issue                     |
|----------------|-------|---------------------------|
| `cli.py`       | 13-61 | Re-exports (keep for now) |
| `types.py`     | 12-40 | Loose contract            |
| `utils/env.py` | -     | Add GitHub context        |

---

## Part 7: Comprehensive Multi-Agent Audit (2026-01-05)

> **Audit Source:** 6 parallel agents examining CLI, services, core, config, utilities, and hub-ci layers.
> **Methodology:** SOLID principles, DRY analysis, CLI best practices from Real Python and clean-code-python.

### 7.1 CLI Layer Consolidation (HIGH PRIORITY)

#### Finding 7.1.1: Argument Definition Duplication
**Problem:** `--output` and `--github-output` defined repeatedly in `hub_ci.py`.

**Files:** `cihub/cli_parsers/hub_ci.py` lines 29, 71, 84, 107, 124, 141, 153, 165, 192, 218, 262, etc.

**Current pattern (anti-pattern):**
```python
# Repeated 28 times with identical help text
hub_ci_actionlint_install.add_argument("--output", help="Write outputs to file")
hub_ci_repo_check.add_argument("--output", help="Write outputs to file")
hub_ci_source_check.add_argument("--output", help="Write outputs to file")
# ... 25 more
```

**Proposed: Centralized argument factory**
```python
# cihub/cli_parsers/common.py
def add_output_args(parser: argparse.ArgumentParser) -> None:
    """Add standard --output and --github-output args."""
    parser.add_argument("--output", help="Write outputs to file")
    parser.add_argument("--github-output", action="store_true", help="Use GITHUB_OUTPUT")

def add_summary_args(parser: argparse.ArgumentParser) -> None:
    """Add standard --summary and --github-summary args."""
    parser.add_argument("--summary", help="Write summary to file")
    parser.add_argument("--github-summary", action="store_true", help="Use GITHUB_STEP_SUMMARY")
```

**Payoff:** Eliminates 60+ lines of repeated argument definitions.

---

#### Finding 7.1.2: Direct Printing in Commands
**Problem:** 261 print() calls across 30 command files instead of returning CommandResult.

**Worst offenders:**
| File | Print Calls | Issue |
|------|-------------|-------|
| `commands/hub_ci/__init__.py` | 15+ | Direct status output |
| `commands/adr.py` | 16 | List/check results |
| `commands/smoke.py` | 12 | Progress output |
| `commands/config_outputs.py` | 8 | Key-value pairs |

**Impact:** `--json` flag cannot capture these outputs.

**Proposed migration:**
```python
# BEFORE (anti-pattern)
def cmd_example(args):
    print(f"Processing: {args.file}")
    if error:
        print(f"Error: {message}", file=sys.stderr)
    return EXIT_FAILURE

# AFTER (correct)
def cmd_example(args) -> CommandResult:
    return CommandResult(
        exit_code=EXIT_FAILURE,
        summary=f"Processing: {args.file}",
        problems=[{"severity": "error", "message": message}],
    )
```

---

#### Finding 7.1.3: Mixed Return Types
**Problem:** Commands inconsistently return `int` or `CommandResult`.

**Evidence:** `cihub/cli.py:383-388` wraps bare ints only in non-JSON mode.

**Files affected:**
- Returns `int`: ~46 hub-ci functions (now migrated ✅)
- Returns `CommandResult`: validate.py, check.py, smoke.py
- Returns both: discover.py, run.py (depending on code path)

**Proposed policy:** All commands MUST return `CommandResult`. CLI wraps `int` during transition.

---

### 7.2 Hub-CI Subcommand Helpers (HIGH PRIORITY)

#### Finding 7.2.1: Output Writing Boilerplate
**Problem:** 15+ occurrences of identical 3-line pattern.

**Current pattern:**
```python
# Repeated in validation.py:62, security.py:216, java_tools.py:133, smoke.py:106, etc.
output_path = _resolve_output_path(args.output, args.github_output)
_write_outputs({"key": "value"}, output_path)
```

**Proposed: Single helper**
```python
# cihub/commands/hub_ci/__init__.py
def write_github_outputs(values: dict[str, str], args: argparse.Namespace) -> None:
    """Write outputs to GitHub or file, resolving paths from args."""
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(values, output_path)
```

---

#### Finding 7.2.2: Tool Status Pattern
**Problem:** 90 lines of identical logic in 3 security commands.

**Files:** `security.py:174-223` (pip_audit), `security.py:226-269` (bandit), `security.py:272-305` (ruff)

**Pattern:**
1. Run command
2. Check if report exists, write fallback if not
3. Set tool_status based on returncode
4. Parse JSON with try/except JSONDecodeError
5. Append problems if failed

**Proposed: Generic helper**
```python
def run_tool_with_json_report(
    cmd: list[str],
    repo_path: Path,
    report_path: Path,
    tool_name: str,
) -> tuple[str, list[dict], dict]:
    """Run tool and parse JSON report. Returns (status, problems, data)."""
```

---

#### Finding 7.2.3: Maven Wrapper Chmod Pattern
**Problem:** 20 lines duplicated 4 times.

**Files:** `java_tools.py:64-71, 89-98, 195-201`, `security.py:314-318`

**Pattern:**
```python
mvnw = repo_path / "mvnw"
if mvnw.exists():
    mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
    _run_command(["./mvnw", ...], repo_path)
```

**Proposed: Helper function**
```python
def ensure_executable_and_run(repo_path: Path, wrapper: str, cmd: list[str]) -> CompletedProcess:
    """Make wrapper executable and run command."""
```

---

### 7.3 Utilities Consolidation (HIGH PRIORITY)

#### Finding 7.3.1: Duplicate Functions
**Problem:** Identical functions in multiple files.

| Function                      | Location 1                | Location 2                   | Lines |
|-------------------------------|---------------------------|------------------------------|-------|
| `_get_repo_name()`            | `report/helpers.py:22-36` | `ci_engine/helpers.py:23-37` | 14    |
| `_detect_java_project_type()` | `report/helpers.py:69-87` | `ci_engine/helpers.py:69-87` | 18    |

**Action:** Move both to `cihub/utils/git.py` or new `cihub/utils/repo.py`.

---

#### Finding 7.3.2: Direct Environment Variable Access
**Problem:** 52 direct `os.environ.get()` calls bypass centralized utilities.

**Available but underused:**
- `cihub/utils/env.py:env_str()` - for string env vars
- `cihub/utils/env.py:env_bool()` - for boolean env vars

**Files bypassing utilities:**
- `report/helpers.py:23, 50, 55-59` - Multiple GITHUB_* vars
- `ci_engine/helpers.py:24` - GITHUB_REPOSITORY
- `ci_engine/gates.py:98-107` - Multiple env reads

**Proposed: Create GitHub env wrapper**
```python
# cihub/utils/github_env.py
@dataclass
class GitHubEnv:
    repository: str | None
    ref_name: str | None
    run_id: str | None
    sha: str | None
    step_summary: Path | None

    @classmethod
    def from_env(cls) -> "GitHubEnv":
        return cls(
            repository=env_str("GITHUB_REPOSITORY"),
            ref_name=env_str("GITHUB_REF_NAME"),
            # ...
        )
```

---

#### Finding 7.3.3: Ad-hoc Subprocess Calls
**Problem:** 30 subprocess.run() calls scattered without consistent patterns.

**Issues:**
- No standardized timeout (varies: 5, 10, 30, 60, 120 seconds)
- Inconsistent error handling for FileNotFoundError
- Mixed `proc.stdout or proc.stderr` patterns

**Proposed: Wrapper function**
```python
# cihub/utils/exec_utils.py
SUBPROCESS_TIMEOUT = 30  # seconds

def safe_run(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int = SUBPROCESS_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """Run subprocess with consistent error handling."""
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {cmd[0]}")
```

---

### 7.4 Core Module Refactoring (MEDIUM PRIORITY)

#### Finding 7.4.1: Report Builder Duplication
**Problem:** `build_python_report()` and `build_java_report()` share 90% code.

**Files:** `core/ci_report.py:142-256` (Python), `core/ci_report.py:259-381` (Java)

**Duplicate blocks:**
- Results structure: lines 180-196 vs 300-316
- Tool metrics extraction: lines 200-219 vs 321-340
- Report assembly: lines 228-255 vs 349-380

**Proposed: Template method**
```python
def _build_report(
    language: str,
    config: dict,
    tool_results: dict,
    context: RunContext,
    metric_extractors: dict[str, Callable],
) -> dict:
    """Generic report builder - language strategies provide extractors."""
```

---

#### Finding 7.4.2: resolve_thresholds() SRP Violation
**Problem:** 82-line function handling 4 concerns.

**File:** `core/ci_report.py:39-121`

**Concerns mixed:**
1. Config parsing (extracting nested dicts)
2. Threshold mapping (standardizing names)
3. Threshold derivation (computing secondary values)
4. Language-specific logic (if/else for python/java)

**Proposed: Split into focused functions**
```python
def _extract_tool_configs(config: dict, language: str) -> dict: ...
def _map_configs_to_thresholds(tool_configs: dict) -> dict: ...
def _derive_secondary_thresholds(thresholds: dict) -> dict: ...
```

Or better: Move into `LanguageStrategy.resolve_thresholds()` method.

---

### 7.5 Config/Schema Consistency (MEDIUM PRIORITY)

#### Finding 7.5.1: Schema Validation Bypass
**Problem:** Hub-CI config loading skips schema validation.

**File:** `commands/hub_ci/__init__.py:90-97`
```python
def _load_config(path: Path | None) -> dict[str, Any]:
    return normalize_config(load_yaml_file(path))  # NO validate_config()!
```

**Risk:** Invalid configs silently proceed.

**Fix:** Call `validate_config()` after `normalize_config()`.

---

#### Finding 7.5.2: Defaults Defined in 4 Places
**Problem:** `fail_on_cvss=7` default in multiple files.

| Location                           | Line     | Value                     |
|------------------------------------|----------|---------------------------|
| `schema/ci-hub-config.schema.json` | 249, 342 | `"default": 7`            |
| `cihub/config/fallbacks.py`        | 15, 47   | `"fail_on_cvss": 7`       |
| `cihub/config/loader/inputs.py`    | 59, 95   | `.get("fail_on_cvss", 7)` |
| `cihub/commands/config_outputs.py` | 107, 118 | `.get("fail_on_cvss", 7)` |

**Risk:** Changing default requires 4-file update.

**Fix:** Define constants module or use schema as single source.

---

### 7.6 Services Layer (MEDIUM PRIORITY)

#### Finding 7.6.1: run_ci() God Method
**Problem:** 300+ line function handling 7 responsibilities.

**File:** `services/ci_engine/__init__.py:128-420`

**Responsibilities:**
1. Config loading/validation (152-166)
2. Strategy selection (178-190)
3. Tool execution (204-207)
4. Report building (270-279)
5. Gate evaluation (280)
6. Self-validation (318-374)
7. Notification dispatch (398)

**Proposed: Extract orchestrator functions**
```python
def run_ci(...) -> CiRunResult:
    config = _load_and_validate_config(...)
    strategy = _select_strategy(config)
    results = _execute_tools(strategy, config)
    report = _build_and_validate_report(results, config)
    _dispatch_notifications(report, config)
    return CiRunResult(...)
```

---

#### Finding 7.6.2: Hardcoded Tool Runner Imports
**Problem:** 19 individual tool runners imported directly.

**File:** `services/ci_engine/__init__.py:17-36`
```python
from cihub.ci_runner import (
    run_bandit,
    run_black,
    run_checkstyle,
    run_docker,
    run_isort,
    run_jacoco,
    run_java_build,
    run_mutmut,
    run_mypy,
    run_owasp,
    run_pip_audit,
    run_pitest,
    run_pmd,
    run_pytest,
    run_ruff,
    run_sbom,
    run_semgrep,
    run_spotbugs,
    run_trivy,
)
```

**Problem:** Adding/changing tool requires modifying this file.

**Proposed: Registry pattern**
```python
from cihub.tools.registry import get_runner

def _execute_tools(strategy, config):
    for tool in strategy.get_default_tools():
        runner = get_runner(tool)  # Dynamic lookup
        results[tool] = runner(...)
```

---

## Part 8: Updated Implementation Roadmap

### Phase 1: Foundation ✅ COMPLETE
- [x] Language strategies (Python/Java)
- [x] Hub-CI CommandResult migration (**46/46 functions**) ✅
- [x] Gate spec wiring (26 thresholds)
- [x] Triage modularization (reference pattern)
- [x] CommandResult helpers (`result_ok`, `result_fail`, `run_and_capture`)
- [x] Strategy kwargs filtering (`get_allowed_kwargs()`)
- [x] Strategy virtual tools (`get_virtual_tools()`)
- [x] Strategy docker config encapsulation (`get_docker_config()`)

### Phase 2: Consolidation Helpers (HIGH PRIORITY)
- [x] Create `cli_parsers/common.py` with `add_output_args()`, `add_summary_args()` ✅ (2026-01-05)
  - 8 factory functions: `add_output_args`, `add_summary_args`, `add_repo_args`, `add_report_args`, `add_path_args`, `add_output_dir_args`, `add_ci_output_args`, `add_tool_runner_args`
  - `hub_ci.py`: 628 → 535 lines (93 lines saved)
  - `report.py` and `core.py` also refactored
  - 30 parameterized tests in `test_cli_common.py`
- [x] Create `cihub/utils/github_context.py` with `OutputContext` dataclass and **migrate all 32 call sites** ✅ (2026-01-05)
  ```python
  @dataclass
  class OutputContext:
      output_path: str | None = None
      github_output: bool = False
      summary_path: str | None = None
      github_summary: bool = False

      def write_outputs(self, values: dict[str, str]) -> None: ...
      def write_summary(self, text: str) -> None: ...
      def has_output(self) -> bool: ...
      def has_summary(self) -> bool: ...

      @classmethod
      def from_args(cls, args) -> "OutputContext": ...
  ```
  - Old pattern: `output_path = _resolve_output_path(...); _write_outputs(values, output_path)`
  - New pattern: `ctx = OutputContext.from_args(args); ctx.write_outputs(values)`
  - Files migrated: `validation.py` (3), `smoke.py` (4), `security.py` (6), `java_tools.py` (4), `python_tools.py` (4), `release.py` (10), `badges.py` (1) = **32 total**
  - Added to `hub_ci/__init__.py` exports (re-exported from utils)
  - 38 tests in `tests/test_output_context.py` (parameterized + Hypothesis property-based)
  - Old 4 helper functions kept for backward compatibility (deprecated)
  - **NOTE:** This replaces Phase 4's `GitHubEnv dataclass` - can extend with env vars later
- [x] Add `hub_ci/__init__.py` tool execution helpers ✅ (2026-01-05)
  - `ToolResult` dataclass: structured result from tool execution
  - `ensure_executable(path)`: consolidates 6 chmod patterns
  - `load_json_report(path, default)`: consolidates 15+ JSON parse patterns
  - `run_tool_with_json_report(cmd, cwd, report_path)`: full tool execution + JSON parsing
  - 39 tests in `tests/test_tool_helpers.py` (parameterized + Hypothesis property-based)
- [x] Consolidate `_get_repo_name()`, `_detect_java_project_type()` to `cihub/utils/project.py` ✅ (2026-01-05)
  - Created `cihub/utils/project.py` with `get_repo_name()` and `detect_java_project_type()`
  - Added underscore aliases for backward compatibility (`_get_repo_name`, `_detect_java_project_type`)
  - Exported via `cihub/utils/__init__.py`
  - Updated import chains:
    - `ci_engine/__init__.py` imports from `cihub.utils`
    - `ci_engine/gates.py` imports `_get_repo_name` from `cihub.utils`
    - `ci_engine/helpers.py` no longer defines these (cleaned up unused `os`, `re` imports)
    - `commands/report/__init__.py` imports from `cihub.utils`
    - `commands/report/helpers.py` imports `_get_repo_name` from `cihub.utils`
    - `commands/report/build.py` imports `_detect_java_project_type` from `cihub.utils`
    - `core/languages/java.py` imports `_detect_java_project_type` from `cihub.utils`
  - 37 tests in `tests/test_utils_project.py` (parameterized edge cases + integration + 6 Hypothesis property-based)
  - Updated 4 test files to patch `cihub.utils.project` instead of old locations

### Phase 3: Output Consistency — Infrastructure Complete, Migration In Progress
- [x] Audit 263+ print() calls in 37 command files ✅ (audit completed 2026-01-05)
- [x] Implement OutputRenderer abstraction (Part 4.1 approach - smarter than utils/output.py) ✅ (2026-01-05)
  - Created `cihub/output/` package with:
    - `__init__.py` - Clean exports
    - `renderers.py` - OutputRenderer ABC, HumanRenderer, JsonRenderer
  - HumanRenderer contains ALL formatting logic (tables, lists, key-values, problems)
  - JsonRenderer uses CommandResult.to_payload() for consistent JSON
  - `get_renderer(json_mode)` factory function
- [x] Centralize output rendering in `cli.py` ✅
  - cli.py now uses `get_renderer()` at lines 394-400
  - Single point of output: `renderer.render(result, command, duration_ms)`
- [x] 35 tests in `tests/test_output_renderers.py` (parameterized + 5 Hypothesis property-based)
- [x] Contract enforcement test (`test_command_output_contract.py`) - prevents regression
- **Architecture:** Commands return CommandResult with data, renderers decide how to display

**Command Migration Progress (2026-01-05):**
| File | Prints Removed | Status |
|------|---------------|--------|
| adr.py | 16 | ✅ Migrated |
| triage.py | 34 | ✅ Migrated |
| secrets.py | 32 | ✅ Migrated |
| templates.py | 22 | ✅ Migrated |
| pom.py | 21 | ✅ Migrated |
| dispatch.py | 10 | ✅ Migrated |
| config_cmd.py | 9 | ✅ Migrated |
| update.py | 8 | ✅ Migrated |
| docs.py | 10 | ✅ Migrated |
| new.py | 10 | ✅ Migrated |
| init.py | 10 | ✅ Migrated |
| smoke.py | 8 | ✅ Migrated |
| discover.py | 8 | ✅ Migrated |
| validate.py | 7 | ✅ Migrated **NEW** |
| detect.py | 3 | ✅ Migrated **NEW** |
| **Total migrated** | **~208** | **15 files** |
| **Remaining** | **~55** | **~7 files + report/ subpkg** |

### Phase 4: Utilities Consolidation
- [ ] Create `cihub/utils/github_env.py` with GitHubEnv dataclass
- [ ] Extend `cihub/utils/exec_utils.py` with `safe_run()` wrapper (file exists)
- [ ] Create `cihub/utils/json_io.py` with `load_json_files()`
- [ ] Replace 51 direct `os.environ.get()` calls with utility functions

### Phase 5: Config/Schema Alignment
- [ ] Add `validate_config()` call to hub_ci._load_config()
- [ ] Define `cihub/config/constants.py` for shared defaults
- [ ] Call `check_threshold_sanity()` during normal config load
- [ ] Document effective-only thresholds vs configurable

### Phase 6: Core Refactoring
- [ ] Extract common report builder template from Python/Java functions
- [ ] Move `resolve_thresholds()` into LanguageStrategy
- [ ] Create `cihub/utils/severity.py` with `count_severities()` helper
- [ ] Add TypedDict or dataclass for report structure

### Phase 7: Services Simplification
- [ ] Split `run_ci()` into 5 focused orchestrator functions
- [ ] Implement tool runner registry pattern
- [ ] Split report_validator.py into schema/content/artifact validators

---

## Appendix B: New Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `cli_parsers/common.py` | **CREATED** ✅ - 8 argument factories | High |
| `utils/github_context.py` | **CREATED** ✅ - OutputContext dataclass (32 call sites migrated) | High |
| `utils/github_env.py` | GitHub env dataclass (extend github_context.py instead) | Medium |
| `utils/exec_utils.py` | **EXISTS** - add `safe_run()` | High |
| `utils/json_io.py` | JSON file operations | Medium |
| `utils/severity.py` | Severity counting | Medium |
| `output/__init__.py` | **CREATED** ✅ - OutputRenderer exports | High |
| `output/renderers.py` | **CREATED** ✅ - HumanRenderer, JsonRenderer (35 tests) | High |
| `config/constants.py` | Shared default values | Medium |
| `tools/registry.py` | Tool runner registry | Medium |

---

## Appendix C: Quick Wins (< 1 hour each)

1. ~~**Create `add_output_args()`**~~ ✅ DONE - Eliminated 36+ duplicate arg definitions
2. **Create `write_github_outputs()`** - Consolidates 15+ output writing patterns
3. **Move `_get_repo_name()`** - Removes exact duplicate
4. **Add `validate_config()`** to hub_ci._load_config() - Fixes validation gap
5. **Create severity counter** - Single function replacing 2 identical if-elif chains

---

## Summary

The codebase has strong foundations (config loading, CLI adapter pattern, ToolResult interface) but suffers from **excessive language branching** that makes it hard to extend.

**One refactor** - extracting Language Strategies - would eliminate 38+ conditionals and make adding new languages trivial.

The other improvements (output consistency, tool adapters, GitHub context) are incremental and can be done file-by-file without breaking changes.

**2026-01-05 Multi-Agent Audit Summary:**
- **50 findings** across 6 codebase areas
- **17 high-priority items** affecting ~3000 lines
- **5 quick wins** achievable in <1 hour each
- **8 new utility files** proposed for consolidation

---

## Part 9: Automation & Infrastructure Consolidation (2026-01-05)

> **Audit Source:** 3 parallel agents examining scripts, workflows, and schemas.
> **Research:** [Google monorepo practices](https://www.bomberbot.com/tech/inside-googles-2-billion-line-codebase-monorepo/), [pre-commit best practices](https://gatlenculp.medium.com/effortless-code-quality-the-ultimate-pre-commit-hooks-guide-for-2025-57ca501d9835), [GitHub Actions consolidation](https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations).

### 9.1 Scripts & Build System (HIGH PRIORITY)

#### Finding 9.1.1: 11 Deprecated Script Shims
**Problem:** `scripts/` directory contains deprecated shims wrapping CLI commands.

| Script | Replacement CLI |
|--------|-----------------|
| `validate_report.sh` | `cihub report validate` |
| `aggregate_reports.py` | `cihub report dashboard` |
| `apply_profile.py` | `cihub config apply-profile` |
| `load_config.py` | `cihub config loader` |
| `render_summary.py` | `cihub report summary` |
| `verify_hub_matrix_keys.py` | `cihub hub-ci verify-matrix-keys` |
| `validate_summary.py` | `cihub report validate` |
| `check_quarantine_imports.py` | `cihub hub-ci quarantine-check` |
| `python_ci_badges.py` | `cihub hub-ci badges` |
| `correlation.py` | `cihub.correlation` module |
| `validate_config.py` | `cihub config validate` |

**Action:** Set removal deadline for next release.

---

#### Finding 9.1.2: Add Black/isort to Local Tooling (Parity Gap)
**Problem:** Black and isort run in CI but NOT locally.

| Environment   | Black/isort Status                                   |
|---------------|------------------------------------------------------|
| CI workflows  | ✅ `run_black`, `run_isort` toggles work              |
| `cihub check` | ❌ Line 328: "Black removed - using Ruff format only" |
| Makefile      | ❌ Only `ruff format`, no black/isort targets         |

**Solution:** Add black/isort to local tooling to match CI behavior.

**1. Update `cihub/commands/check.py`:**
```python
# Remove line 328 comment and add:
add_step("black", _run_process("black", ["black", "--check", "."], root))
add_step("isort", _run_process("isort", ["isort", "--check-only", "."], root))
```

**2. Add Makefile targets:**
```makefile
.PHONY: format-black
format-black: ## Run black formatter
	black cihub/ tests/ scripts/

.PHONY: format-isort
format-isort: ## Run isort import sorter
	isort cihub/ tests/ scripts/

.PHONY: format-all
format-all: format format-black format-isort ## Run all formatters
```

**Result:** `make check` and `make verify` will run all formatters like CI does.

---

#### Finding 9.1.3: Pre-commit Missing JSON Schema Validation
**Add to `.pre-commit-config.yaml`:**
```yaml
- repo: https://github.com/python-jsonschema/check-jsonschema
  rev: 0.29.1
  hooks:
    - id: check-jsonschema
      files: '^config/.*\\.yaml$'
      args: ['--schemafile=schema/ci-hub-config.schema.json']
```

---

### 9.2 GitHub Workflows Security (MEDIUM PRIORITY)

> **Note:** Composite actions were evaluated but REJECTED to preserve the boolean-toggle
> workflow architecture. Each workflow remains explicit and self-contained.

#### Finding 9.2.1: Missing Harden-Runner
**Add `step-security/harden-runner` to:**
- python-ci.yml, java-ci.yml
- hub-orchestrator.yml (3 jobs)
- hub-run-all.yml (2 jobs)
- hub-security.yml (4 jobs)
- smoke-test.yml (3 jobs)

---

### 9.3 Schema Consolidation ✅ DONE

**Status:** COMPLETE (2026-01-05)

**Problem (SOLVED):** Schema duplication causing ~150 lines of redundant definitions.

**Migration (COMPLETED):**
1. ✅ Added `sharedSbomTool` and `sharedSemgrepTool` to `#/definitions` in ci-hub-config.schema.json
2. ✅ Updated `javaTools.sbom` and `javaTools.semgrep` to use `$ref`
3. ✅ Updated `pythonTools.sbom` and `pythonTools.semgrep` to use `$ref`
4. ✅ Added `toolStatusMap` definition to ci-report.v2.json
5. ✅ Updated `tools_ran`, `tools_configured`, `tools_success`, `tools_require_run` to use `$ref`
6. ✅ Fixed `test_tools_ran_schema_covers_all_tools` to follow `$ref`
7. ✅ All 2104 tests pass

**Benefit:** ~100 lines removed, single source of truth for tool definitions, easier maintenance.

**Note:** docker, trivy, codeql remain inline because they have language-specific defaults (e.g., `languages: ["java"]` vs `["python"]`).

#### Finding 9.3.1: Shared Tools Duplicated (RESOLVED)
**Problem:** 5 tools defined identically in javaTools AND pythonTools.

| Tool    | Duplicate Lines | Status |
|---------|-----------------|--------|
| docker  | 34              | ⚠️ Different defaults (has `dockerfile` in Java) |
| trivy   | 30              | ⚠️ Different defaults (Java has `fail_on_cvss`) |
| codeql  | 28              | ⚠️ Different defaults (`languages` differs) |
| sbom    | 26              | ✅ EXTRACTED to `sharedSbomTool` |
| semgrep | 28              | ✅ EXTRACTED to `sharedSemgrepTool` |

**Fix:** Extracted identical tools (sbom, semgrep) to `#/definitions/sharedTools` (~54 lines removed)

---

#### Finding 9.3.2: Triple Default Definition
**Problem:** Same defaults in 3 places.

| Source | File                               |
|--------|------------------------------------|
| Schema | `schema/ci-hub-config.schema.json` |
| YAML   | `config/defaults.yaml`             |
| Python | `cihub/config/fallbacks.py`        |

**Fix:** Generate YAML and Python FROM schema (single source of truth).

---

#### Finding 9.3.3: Report Schema Tool Lists (RESOLVED)
**Problem:** 4 identical 22-tool lists in `ci-report.v2.json`.

**Fix:** ✅ Extracted to `#/definitions/toolStatusMap`, referenced 4x (~66 lines removed).

---

#### Finding 9.3.4: Optional Features Unvalidated
**Problem:** `canary`, `chaos`, etc. have `additionalProperties: true`.

**Fix:** Create full schema definitions for each optional feature.

---

### 9.4 Implementation Phases

#### Phase 1: Scripts & Tooling (Immediate)
- [x] Remove deprecated script entry points from pyproject.toml ✅ 2026-01-05
- [x] Set removal date for 11 script shims ✅ 2026-01-05 (removal: 2026-02-01)
- [x] Add black/isort to `cihub check` (match CI parity) ✅ 2026-01-05
- [x] Add `format-black`, `format-isort`, `format-all` Makefile targets ✅ 2026-01-05
- [ ] Add JSON schema validation to pre-commit

#### Phase 2: Workflow Security (1 day)
- [ ] Add harden-runner to 8 missing workflows
- [ ] Verify action pinning is consistent

#### Phase 3: Schema Consolidation ✅ COMPLETE (2026-01-05)
- [x] Extract `sharedTools` definition (sbom, semgrep)
- [x] Extract `toolStatusMap` definition (22-tool boolean map)
- [ ] Add full schemas for optional features (DEFERRED - low priority)

#### Phase 4: Config Generation (2-3 days)
- [ ] Script to generate `defaults.yaml` from schema
- [ ] Script to generate `fallbacks.py` from schema
- [ ] Add CI check for schema-defaults alignment

---

### 9.5 Industry Best Practices Checklist

| Practice                   | Status | Action                                      |
|----------------------------|--------|---------------------------------------------|
| Trunk-based development    | ✅      | Already using                               |
| Multiple formatter support | ✅      | CI has black/isort; local tooling updated ✅ |
| Action pinning             | ✅      | All pinned to SHAs                          |
| Pre-commit automation      | ⚠️     | Add schema validation                       |
| Explicit workflows         | ✅      | Boolean-toggle architecture preserved       |
| Single source of truth     | ❌      | Schema → generate configs                   |
| Pydantic validation        | ❌      | Consider for config types                   |
| Security hardening         | ⚠️     | Add harden-runner to 8 workflows            |

**2026-01-05 Automation Audit Summary:**
- **14 workflows** with security hardening opportunities
- **11 deprecated scripts** ready for removal
- **~400 lines** of schema duplication
- **Triple default definition** problem
- **Local/CI parity gap** - Add black/isort to `cihub check` and Makefile

---

## Part 10: Testing Improvements (2026-01-05)

> **Audit Source:** Analysis of test patterns + research on pytest best practices.
> **Research:** [Pytest Parameterized Tests](https://pytest-with-eric.com/introduction/pytest-parameterized-tests/), [Hypothesis Property-Based Testing](https://pytest-with-eric.com/pytest-advanced/hypothesis-testing-python/), [Python Testing Frameworks 2025](https://www.geeksforgeeks.org/python/best-python-testing-frameworks/), [Mutation Testing Guide](https://mastersoftwaretesting.com/testing-fundamentals/types-of-testing/mutation-testing)

### 10.1 Current Testing State

| Metric                           | Current             | Opportunity               |
|----------------------------------|---------------------|---------------------------|
| Test files                       | 70                  | -                         |
| `@pytest.mark.parametrize` usage | 25 uses in 6 files  | Expand to 30+ files       |
| `@pytest.fixture` usage          | 68 uses in 18 files | Centralize in conftest.py |
| Hypothesis (property-based)      | 25 uses in 5 files  | Expand to critical paths  |
| Mutmut (mutation testing)        | ✅ Configured        | Already integrated        |
| conftest.py                      | ❌ Missing           | Create shared fixtures    |
| pytest-xdist (parallel)          | ❌ Missing           | Add for faster CI         |

### 10.2 Missing Testing Patterns

#### Finding 10.2.1: No conftest.py for Shared Fixtures
**Problem:** Fixtures are duplicated across test files instead of centralized.

**Create `tests/conftest.py`:**
```python
"""Shared pytest fixtures for all tests."""
import pytest
from pathlib import Path

@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary repository structure."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    return tmp_path

@pytest.fixture
def sample_config() -> dict:
    """Return a minimal valid config."""
    return {
        "python": {"tools": {"pytest": {"enabled": True}}},
        "thresholds": {"coverage_min": 70},
    }

@pytest.fixture
def mock_env(monkeypatch):
    """Factory for mocking environment variables."""
    def _mock(**env_vars):
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
    return _mock
```

---

#### Finding 10.2.2: Underutilized Parameterized Testing
**Problem:** Only 6/70 test files use `@pytest.mark.parametrize`.

**High-value candidates for parameterization:**

| Test File               | Current Tests         | Parameterize Opportunity |
|-------------------------|-----------------------|--------------------------|
| `test_config_module.py` | Individual tool tests | All tool configs         |
| `test_ci_report.py`     | Python/Java separate  | Language matrix          |
| `test_services_ci.py`   | Individual services   | Service operations       |
| `test_hub_ci.py`        | Per-command tests     | Command matrix           |
| `test_cli_commands.py`  | Per-command tests     | CLI subcommands          |

**Example refactor:**
```python
# Before: 10 separate tests
def test_pytest_config(): ...
def test_ruff_config(): ...
def test_bandit_config(): ...

# After: 1 parameterized test
@pytest.mark.parametrize("tool", ["pytest", "ruff", "bandit", "mypy", "black"])
def test_tool_config(tool, sample_config):
    assert tool in sample_config["python"]["tools"]
```

---

#### Finding 10.2.3: Expand Hypothesis Property-Based Testing
**Problem:** Hypothesis only used in 5 files despite being installed.

**High-value Hypothesis candidates:**

| Module                         | Property to Test                                |
|--------------------------------|-------------------------------------------------|
| `config/normalize.py`          | Threshold profiles always produce valid configs |
| `config/schema.py`             | Any valid config passes validation              |
| `core/ci_report.py`            | Report builder handles any tool combination     |
| `core/gate_specs.py`           | Gates evaluate consistently for boundary values |
| `services/report_validator.py` | Validator catches all invalid reports           |

**Example:**
```python
from hypothesis import given, strategies as st

@given(coverage=st.integers(min_value=0, max_value=100))
def test_coverage_threshold_boundary(coverage):
    """Property: coverage_min must be 0-100."""
    config = {"thresholds": {"coverage_min": coverage}}
    result = validate_thresholds(config)
    assert result.success == (0 <= coverage <= 100)
```

---

#### Finding 10.2.4: Missing pytest-xdist for Parallel Execution
**Problem:** Tests run sequentially; CI could be faster.

**Add to pyproject.toml:**
```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "pytest-xdist>=3.0",  # Parallel test execution
]

[tool.pytest.ini_options]
addopts = "-n auto"  # Auto-detect CPU cores
```

**Expected improvement:** 30-50% faster test runs on multi-core CI runners.

---

#### Finding 10.2.5: Consider Contract Testing for APIs
**Problem:** No contract tests between services and consumers.

**For future consideration (not immediate):**
- `pact-python` for consumer-driven contracts
- `icontract` for design-by-contract assertions

---

### 10.3 Testing Implementation Phases

#### Phase T1: Foundation (Immediate)
- [x] Create `tests/conftest.py` with shared fixtures ✅ 2026-01-05
- [x] Add `pytest-xdist` for parallel execution ✅ 2026-01-05
- [x] Add `hypothesis` to dev dependencies ✅ 2026-01-05
- [x] Identify 10 test files for parameterization ✅ 2026-01-05

#### Phase T2: Parameterization (1-2 days)
- [x] Refactor `test_config_module.py` with PathConfig matrix ✅ 2026-01-05
- [x] Refactor `test_ci_engine.py` with Java project type matrix ✅ 2026-01-05
- [x] Refactor `test_hub_ci.py` with command matrix ✅ 2026-01-05
- [x] Refactor `test_language_strategies.py` with strategy matrix ✅ 2026-01-05
- [x] Refactor `test_cihub_cli.py` with subcommand matrix ✅ 2026-01-05

#### Phase T3: Property-Based Testing (1-2 days)
- [x] Create `tests/test_property_based.py` with Hypothesis ✅ 2026-01-05
- [x] Add Hypothesis tests for deep_merge properties ✅ 2026-01-05
- [x] Add Hypothesis tests for threshold boundaries ✅ 2026-01-05
- [x] Add Hypothesis tests for tool config properties ✅ 2026-01-05
- [x] Add Hypothesis tests for report structure invariants ✅ 2026-01-05

#### Phase T4: Integration (Ongoing)
- [ ] Run parameterized tests with each PR
- [ ] Track mutation testing scores
- [ ] Add contract tests as services grow

---

### 10.4 Testing Best Practices Checklist

| Practice                      | Status | Action                        |
|-------------------------------|--------|-------------------------------|
| Shared fixtures (conftest.py) | ✅      | Created `tests/conftest.py` ✅ |
| Parameterized tests           | ⚠️     | Expand from 6 to 30+ files    |
| Property-based (Hypothesis)   | ⚠️     | Expand from 5 to 15+ files    |
| Mutation testing (mutmut)     | ✅      | Already configured            |
| Parallel execution (xdist)    | ✅      | Added `pytest-xdist>=3.0` ✅   |
| Coverage gates                | ✅      | 70% minimum enforced          |
| Snapshot testing              | ⚠️     | Have some, could expand       |

**2026-01-05 Testing Audit Summary:**
- **70 test files** with room for consolidation
- ~~Parameterized testing underutilized (6/70 files)~~ → Now 10+ files with parameterized tests ✅
- ~~Hypothesis underutilized (5/70 files)~~ → Added `test_property_based.py` with 12 tests ✅
- ~~No conftest.py~~ → Created `tests/conftest.py` ✅
- ~~pytest-xdist missing~~ → Added to dev dependencies ✅

**Refactored Test Files (2026-01-05):**
- `test_config_module.py`: PathConfig matrix (8 tests → 2 parameterized)
- `test_ci_engine.py`: Java project type matrix (6 tests → 1 parameterized)
- `test_hub_ci.py`: TestExtractCount, TestCountPipAuditVulns, TestResolveOutputPath, TestCmdZizmorCheck
- `test_language_strategies.py`: TestStrategyCommonBehavior, TestStrategyDetection, TestJavaBuildToolDetection
- `test_cihub_cli.py`: TestSafeUrlopen (URL schemes), TestMainFunction (JSON output, info flags)
- `test_output_context.py`: **NEW** 38 tests for OutputContext (parameterized + Hypothesis property-based)
- `test_tool_helpers.py`: **NEW** 39 tests for ToolResult, ensure_executable, load_json_report, run_tool_with_json_report
- `test_utils_project.py`: **NEW** 37 tests for get_repo_name, detect_java_project_type (parameterized + integration + 6 Hypothesis property-based)
