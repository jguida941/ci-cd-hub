# Clean Code Audit: Scalability & Architecture Improvements (Archived)
> **Superseded by:** [MASTER_PLAN.md](../MASTER_PLAN.md)  

> **WARNING: SUPERSEDED:** This document is archived (2026-01-15). The canonical execution plan is
> `docs/development/MASTER_PLAN.md`, with current architecture in `docs/development/architecture/ARCH_OVERVIEW.md`.
>
> **Status:** Archived  
> **Archived:** 2026-01-15
> **Owner:** Development Team  
> **Source-of-truth:** manual  
> **Last-reviewed:** 2026-01-15  
> **Superseded-by:** docs/development/MASTER_PLAN.md  

**Date:** 2026-01-04  
**Last Updated:** 2026-01-15 (Status reconciliation: test count policy applied)  
**Branch:** feat/modularization
**Progress:** Complete (Phase T4 contains ongoing process items tracked in TEST_REORGANIZATION.md)
**Purpose:** Identify opportunities for polymorphism, encapsulation, and better modular boundaries to make the codebase more scalable.

> NOTE: The MASTER_PLAN accuracy audit was completed on 2026-01-15.

---

## 🆕 Current Work (2026-01-06): Hub Operational Settings

**Completed:** Config-file-first architecture for hub-internal workflows (ADR-0049)

### Problem Solved

Hub-internal workflows (`hub-run-all.yml`, `hub-orchestrator.yml`) had 10+ boolean inputs for operational settings (debug flags, security policies, execution toggles). This created:
- No persistent state for default behavior changes
- Risk of hitting GitHub's 25-input limit as features grew
- Manual workflow editing required for default changes

### Solution Implemented

**Config-file-first pattern:** Settings live in `cihub/data/config/hub-settings.yaml`, workflow inputs become overrides.

```
Precedence: workflow_dispatch inputs → cihub/data/config/hub-settings.yaml → built-in defaults
```

### Files Created/Modified

| File | Purpose |
|------|---------|
| `cihub/data/config/hub-settings.yaml` | Hub operational settings (execution, debug, security) |
| `cihub/data/schema/hub-settings.schema.json` | Validation schema |
| `cihub/commands/hub_config.py` | CLI command implementation |
| `cihub/cli_parsers/hub.py` | CLI parser for `cihub hub config` commands |
| `.github/workflows/hub-run-all.yml` | Added `load-settings` job |
| `.github/workflows/hub-orchestrator.yml` | Added `load-settings` job |
| `docs/adr/0049-hub-operational-settings.md` | Architecture decision record |

### CLI Commands Added

```bash
cihub hub config show # View current settings
cihub hub config set debug.enabled true # Change a setting
cihub hub config load --github-output # Export for GitHub Actions
```

### Config Hierarchy (Now Two-Layered)

```
Hub Operational Settings (ADR-0049):
 cihub/data/config/hub-settings.yaml → controls HOW hub runs

Per-Repo Tool Configs (ADR-0002, ADR-0024):
 1. .ci-hub.yml (repo-local)
 2. cihub/data/config/repos/<repo>.yaml (hub-side)
 3. cihub/data/config/defaults.yaml (global)
 → controls WHAT runs on each repo
```

---

## Master Checklist (AI Navigation Aid)

Use this checklist to track overall progress. Detailed implementation notes are in the referenced sections.

### Completed [x]

- [x] **Part 1.5:** Triage Package Modularization (Reference Pattern)
- [x] **Part 1.6:** Gate Specs Infrastructure (26 thresholds wired)
- [x] **Part 2.2a:** Hub-CI CommandResult Gap (46 functions migrated)
- [x] **Part 2.4:** Consolidate `_tool_enabled()` (1 canonical + 4 delegates)
- [x] **Part 5.1 Phase 1:** Remove CLI re-export comments (411→366 lines)
- [x] **Part 5.4:** CLI Command Sprawl audit (BY DESIGN - API endpoints)
- [x] **Phase 1:** Foundation (Language strategies extracted)
- [x] **Part 10 Phase T1-T3:** Testing foundation, parameterization, property-based

### High Priority (In Progress)

- [x] **Part 2.1:** Extract Language Strategies [x] **DONE** (cihub/core/languages/ exists with base.py, python.py, java.py, registry.py)
- [x] **Part 2.2:** Centralize Command Output [x] **DONE** (84% reduction - remaining prints are intentional helpers/progress in hub-ci)
- [x] **Part 2.7:** Consolidate ToolResult [x] **DONE** (unified in `cihub/types.py`, re-exported for backward compat)
- [x] **Part 7.1:** CLI Layer Consolidation [x] **DONE** (common.py factory exists, 7.1.2/7.1.3 done in Part 2.2/5.2)
- [x] **Part 7.2:** Hub-CI Subcommand Helpers [x] **DONE** (write_github_outputs, run_tool_with_json_report, ensure_executable exist)
- [x] **Part 7.3:** Utilities Consolidation [x] **DONE** (7.3.1 [x] project.py, 7.3.2 [x] github_context.py, 7.3.3 [x] safe_run() wrapper + 34 migrations)
- [x] **Part 9.3:** Schema Consolidation [x] **DONE** (sbom/semgrep → sharedTools, toolStatusMap extracted)

### 7-Agent Audit Fixes (COMPLETE - 2026-01-06)

> **Source:** 7-agent comprehensive code review. **All 5 critical fixes applied, 2263 tests pass.**

- [x] **fix.py JSON parsing:** Silent failure → log warning + add to problems (lines 174-175, 192-193) [x]
- [x] **triage.py None propagation:** Add explicit None check after `_find_report_in_artifacts()` (lines 792-799) [x]
- [x] **triage.py repo validation:** Add regex validation for `owner/repo` format (lines 842-851) [x]
- [x] **release.py urllib timeout:** Add `timeout=60` parameter (line 81, ADR-0045) [x]
- [x] **templates.py token validation:** Validate token format before env var set (lines 52-71) [x]

### Medium Priority (Pending)

- [x] **Part 2.5:** Expand CI Engine Tests [x] **DONE** (131+ tests: test_ci_engine.py 124 tests, test_ci_env_overrides.py 5 tests, test_services_ci.py 2 tests)
- [x] **Part 2.6:** Gate Evaluation Refactor [x] **DONE** (gate_specs.py with 26 thresholds wired to evaluate_threshold)
- [x] **Part 3.1:** Centralize GitHub Environment Access [x] **DONE** (unified GitHubContext: 11 env vars + output/summary writing, 59 tests)
- [x] **Part 3.2:** Consolidate RunCI Parameters [x]
- [x] **Part 5.1:** CLI re-exports cleanup [x] **DONE** (removed 50+ re-exports, fixed imports directly)
- [x] **Part 5.2:** Mixed Return Types [x] **DONE** (all 47 commands → pure CommandResult)
- [x] **Part 5.3:** Special-Case Handling [x] **DONE** (2026-01-10: Tool adapter registry in cihub/tools/registry.py, 10 new tests)
- [x] **Part 7.4:** Core Module Refactoring [x] **DONE** (7.4.1-7.4.8 all complete)
- [x] **Part 7.5:** Config/Schema Consistency [x] **DONE** (schema validation bypass fixed in hub_ci/__init__.py)
- [x] **Part 7.6:** Services Layer [x] **DONE** (7.6.1 partial by design, 7.6.2-7.6.4 complete)
- [x] **Part 9.1:** Scripts & Build System [x] **DONE** (deprecation warnings added, docs updated, pre-commit JSON schema validation added; Black/isort skipped - Ruff is intentional replacement)
- [x] **Part 9.2:** GitHub Workflows Security [x] **DONE** (harden-runner added as configurable toggle: schema `harden_runner.policy`, workflow input `harden_runner_policy` with values audit/block/disabled)

### Low Priority / Deferred

- [x] **Part 2.3:** Tool Adapter Registry [x] **DONE** (cihub/tools/registry.py with Python + Java adapters)
- [ ] **Part 3.3:** Tighten CommandResult Contract (DEFERRED)
- [x] **Part 4.1:** Output Renderer Abstraction [x] (implemented 2026-01-05)
- [x] **Part 4.2:** Filesystem/Git Abstractions for Testing
- [ ] **Part 10 Phase T4:** Integration testing (Ongoing)

### Final Validation

- [x] All CI tests pass (count tracked in STATUS.md)
- [~] Mutation testing score maintained (deferred - time-intensive)
- [x] `MASTER_PLAN.md` audit for accuracy **DONE** (2026-01-15 - all data verified accurate)
- [x] Documentation reflects new architecture (CLEAN_CODE.md updated throughout)

---

## Audit Update (2026-01-05) - Comprehensive Multi-Agent Audit

**NEW:** Part 7 contains results from 6 parallel audit agents covering CLI, services, core, config, utilities, and hub-ci layers. **50 findings identified, 17 high-priority.**

Multi-agent audit validated this document remains **~85% accurate**. Key updates:

| Finding | Original | Updated | Status |
|-----------------------|---------------|---------------------------------------------------------|------------------|
| Language branches | 38+ | **46 found** | [x] Still accurate |
| gate_specs.py | Not mentioned | **COMPLETE: 26 thresholds wired to evaluate_threshold** | [x] Fixed |
| Print in commands | "scattered" | **37 files, 46 hub-ci bare int** | WARNING: Under-scoped |
| _tool_enabled() | 5 places | **COMPLETE: 1 canonical + 4 delegates** | [x] Fixed |
| Triage modularization | N/A | **COMPLETED - Reference pattern** | New example |

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

## 7-Agent Audit Findings (2026-01-06) - TO BE ADDRESSED

> Source: Comprehensive 7-agent code review. Items below are NEW findings not yet addressed.

### Critical (Fix Before Release)

| Severity | Issue | File:Lines | Fix |
|----------|-------|-----------|-----|
| Critical | JSON parsing silently fails | `fix.py:174-175, 192-193` | `except json.JSONDecodeError: pass` → log warning + add to CommandResult.problems |
| Critical | Triage None propagation | `triage.py:789-806` | Add explicit None check after `_find_report_in_artifacts()` → return EXIT_FAILURE |

### High (Security Validation)

| Severity | Issue | File:Lines | Fix |
|----------|-------|-----------|-----|
| High | Repo name not validated | `triage.py:293-295` | Add regex validation for `owner/repo` format before use |
| High | Missing urllib timeout | `release.py:78-81` | Add `timeout=60` parameter (ADR-0045 compliance) |
| High | Token pollution | `templates.py:52-53` | Validate token format before setting environment variable |

### Related Coverage

- **Registry tests:** See REGISTRY_AUDIT_AND_PLAN.md Part 15 (comprehensive test strategy)
- **Service tests:** See TEST_REORGANIZATION.md for 9 untested service modules
- **Doc contradictions:** See DOC_AUTOMATION_AUDIT.md for 12 documentation inconsistencies

---

## Executive Summary

| Aspect | Current Score | Key Issue |
|--------------------|---------------|---------------------------------------------------------------------------------|
| CLI Layer | 8/10 | Thin adapter [x], but output handling inconsistent |
| **CLI UX** | 8/10 | 28 commands [x] BY DESIGN (API endpoints for TS/GUI - see Part 5.4) |
| Command Contracts | 9/10 | [x] **DONE:** 84% reduction, remaining prints are intentional hub-ci helpers |
| Language Branching | 3/10 | **46 if-language checks** - major polymorphism opportunity |
| Tool Runners | 7/10 | Unified ToolResult, but manual dispatch logic |
| Config Loading | 9/10 | Excellent - centralized facade with schema validation |
| Context/State | 7/10 | Context exists but `run_ci()` has 9 keyword params |
| Output Formatting | 9/10 | **COMPLETE: All 46 hub-ci functions return CommandResult** |
| Env Toggles | 7/10 | Helpers exist, GitHub env reads scattered |
| **Gate Specs** | 9/10 | **COMPLETE: 26 threshold checks wired to evaluate_threshold** |
| **Triage Package** | 9/10 | **Excellent modularization - reference pattern** |

**Biggest Win:** Extract Language Strategies to eliminate 46 conditional branches.

---

## Part 1: What's Working Well

### 1.1 CLI as Thin Adapter [x]

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

### 1.2 Config Loading [x]

Single canonical path with proper facade:

```
cihub/ci_config.py (entry point)
 └── cihub/config/loader/core.py (schema validation + merge)
 └── cihub/config/loader/__init__.py (clean re-exports)
```

All 10+ files that load config use the same path. Deep merge maintains precedence. Schema validation catches errors early.

### 1.3 Tool Runner Interface [x]

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

### 1.4 CommandResult Contract [x]

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

### 1.5 Triage Package Modularization [x] (Reference Pattern)

**Completed:** 2026-01-05

`cihub/services/triage/` demonstrates the recommended modularization approach:

```
cihub/services/triage/ # 711 lines across 4 files
├── __init__.py (68 lines) # Clean facade/re-exports
├── types.py (135 lines) # Data models (ToolStatus, ToolEvidence, TriageBundle)
├── evidence.py (339 lines) # Tool evidence building
└── detection.py (169 lines) # Flaky test/regression detection
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

### 1.6 Gate Specs Infrastructure [x] COMPLETE

`cihub/core/gate_specs.py` defines declarative gate specifications, now **fully wired** into gates.py.

```python
@dataclass(frozen=True)
class ThresholdSpec:
 label: str # "Min Coverage"
 key: str # "coverage_min"
 comparator: Comparator # GTE/LTE/CVSS
 metric_key: str # "coverage"
 failure_template: str # "coverage {value}% < {threshold}%"

PYTHON_THRESHOLDS: tuple[ThresholdSpec, ...] = (...)
JAVA_THRESHOLDS: tuple[ThresholdSpec, ...] = (...)
```

**What's now used:**
- `gates.py` imports `get_tool_keys()`, `evaluate_threshold`, `get_threshold_spec_by_key` [x]
- `reporting.py` imports `threshold_rows`/`tool_rows` for summary rendering [x]
- **NEW:** `_check_threshold()` helper wires 26 threshold checks to `evaluate_threshold` [x]

**Implementation (2026-01-05):**
- Added `_check_threshold()` helper to `gates.py`
- Defined 27 ThresholdSpecs in gate_specs.py (Python: 15, Java: 12)
- Refactored Python gates (14 checks): coverage, mutation, ruff, black, isort, mypy, bandit (high/medium/low), pip_audit, semgrep, trivy (critical/high/cvss)
- Refactored Java gates (12 checks): coverage, mutation, checkstyle, spotbugs, pmd, owasp (critical/high/cvss), trivy (critical/high/cvss), semgrep
- All 155 gate-related tests pass - no behavior changes, consistent failure messages

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
- [x] `cihub/services/ci_engine/__init__.py` - Uses strategy for tool execution, report building, gate evaluation
- [x] `cihub/services/ci_engine/helpers.py` - `_apply_force_all_tools()` uses `strategy.get_default_tools()`
- `cihub/services/ci_engine/gates.py` - Gate logic remains, strategies delegate to it (by design)
- `cihub/commands/hub_ci/validation.py` - N/A (file patterns, not tool lists)

**Payoff:**
- Adding Go/Rust/TypeScript = one new file, zero modifications
- Testing: mock strategy, verify calls
- No more duplicate gate logic

---

### 2.2 Centralize Command Output (HIGH) - In Progress

**Problem:** Commands print directly instead of returning structured results.  

**2026-01-05 Progress Update:** Significant progress made on migration:
- ~~**37 files**~~ → **~16 files** in `cihub/commands/` contain direct `print()` calls
- ~~**263+ print() calls**~~ → **~65 print() calls** remaining (~198 migrated)
- **46 hub-ci functions** return CommandResult [x] (complete)
- **13 major command files migrated:** adr.py (16), triage.py (34), secrets.py (32), templates.py (22), pom.py (21), dispatch.py (10), config_cmd.py (9), update.py (8), smoke.py (8), discover.py (8), docs.py (10), new.py (10), init.py (10)
- Contract enforcement test prevents regression on migrated files

**Remaining violations (top offenders):**

| File | Print Calls | Issue |
|-------------------------------|-------------|-------------------------|
| `commands/validate.py` | 7 | Validation output |
| `commands/run.py` | 6 | CI run output |
| `commands/scaffold.py` | 5 | Scaffolding output |
| `commands/check.py` | 5 | Check output |
| `commands/ci.py` | 4 | CI info output |
| `commands/preflight.py` | 3 | Preflight checks |
| `commands/detect.py` | 3 | Detection output |
| `commands/verify.py` | 2 | Verification output |
| `commands/config_outputs.py` | 2 | Config output |
| `commands/report/` subpkg | ~8 files | Various report outputs |

**Migrated (no longer in allowlist):**
- ~~`commands/pom.py`~~ (21 prints) [x]
- ~~`commands/secrets.py`~~ (32 prints) [x]
- ~~`commands/templates.py`~~ (22 prints) [x]
- ~~`commands/triage.py`~~ (34 prints) [x]
- ~~`commands/adr.py`~~ (16 prints) [x]
- ~~`commands/dispatch.py`~~ (10 prints) [x]
- ~~`commands/config_cmd.py`~~ (9 prints) [x]
- ~~`commands/update.py`~~ (8 prints) [x]
- ~~`commands/docs.py`~~ (10 prints) [x]
- ~~`commands/new.py`~~ (10 prints) [x]
- ~~`commands/init.py`~~ (10 prints) [x]
- ~~`commands/smoke.py`~~ (8 prints) [x] **NEW 2026-01-05**
- ~~`commands/discover.py`~~ (8 prints) [x] **NEW 2026-01-05**
- **All hub-ci subcommands** → [x] **46 functions return CommandResult**

**Current anti-pattern:**
```python
# commands/run.py:67-71
def cmd_run(args):
 # ...
 if json_mode:
 return CommandResult(exit_code=EXIT_FAILURE, summary=message)
 print(message) # <-- Layer violation!
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
 details=traceback_if_debug, # Human-readable details
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
 print(f" {problem['message']}", file=sys.stderr)

 return result.exit_code
```

**Payoff:**
- Guaranteed JSON output works for all commands
- Testing: assert on CommandResult, not stdout capture
- Consistent user experience

---

### 2.2a Hub-CI CommandResult Gap [x] COMPLETE

**Problem:** All 46 hub-ci subcommands returned bare `int`, breaking `--json` support.  

**2026-01-05 Final Status:** All 46 functions migrated to CommandResult.

**Migration Progress (2026-01-05):**
| File | Functions | Status |
|------|-----------|--------|
| `cihub/commands/hub_ci/validation.py` | 8 functions | [x] Complete |
| `cihub/commands/hub_ci/security.py` | 6 functions | [x] Complete |
| `cihub/commands/hub_ci/smoke.py` | 4 functions | [x] Complete |
| `cihub/commands/hub_ci/python_tools.py` | 3 functions | [x] Complete |
| `cihub/commands/hub_ci/java_tools.py` | 6 functions | [x] Complete |
| `cihub/commands/hub_ci/release.py` | 16 functions | [x] Complete |
| `cihub/commands/hub_ci/badges.py` | 3 functions | [x] Complete |
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
- Full `--json` support for automation [x]
- Consistent testing via CommandResult assertions [x]
- Triage can consume structured hub-ci results [x]

---

### 2.3 Tool Adapter Registry (DONE)

**Status:** COMPLETE (ToolAdapter registry implemented in `cihub/tools/registry.py`)  

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
 result = execute_spec(spec) # Centralized subprocess handling
 result = adapter.post_process(result)
 results[adapter.name] = result
 return results
```

**Payoff:**
- Adding new tool = one adapter class
- Config extraction tested in isolation
- Subprocess calls fully centralized

---
### 2.4 Consolidate `_tool_enabled()` [x] COMPLETE

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
### 2.5 Expand CI Engine Tests (HIGH) [x] COMPLETE

**Status:** DONE (2026-01-06)  

**Problem:** `tests/test_services_ci.py` originally covered only two scenarios.  

**Solution:** Comprehensive test coverage now exists across multiple files:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_ci_engine.py` | 124 | Gate evaluation, tool config, thresholds (Python & Java) |
| `test_ci_env_overrides.py` | 5 | `CIHUB_RUN_*`, `CIHUB_WRITE_GITHUB_SUMMARY` overrides |
| `test_services_ci.py` | 2 | Original integration tests |
| **Total** | **131+** | All requirements satisfied |

**All original requirements now covered:**
- [x] Mock adapters simulating tool outcomes (TestToolEnabled, TestToolGateEnabled)
- [x] Gate evaluation for coverage/mutation/security (TestEvaluatePythonGates, TestEvaluateJavaGates)
- [x] Env overrides (test_ci_env_overrides.py + test_summary_commands.py)
- [x] Both Python and Java strategies covered

**Benefit:** High confidence in gate/runner changes; comprehensive regression coverage.

---
### 2.6 Gate Evaluation Refactor (MEDIUM)

**Problem:** `_evaluate_python_gates` and `_evaluate_java_gates` duplicate long `if` chains for coverage/mutation/security thresholds.  

**Plan:**
- Define declarative gate specs (e.g., `Gate(name="coverage", metric="coverage", threshold_key="coverage_min")`).
- Each language strategy supplies its gate list, and a shared evaluator applies the specs.
- Pass actual metrics + thresholds into the evaluator to produce failure details consistently.

**Benefit:** Removing duplicated logic, easier to add/remove gates, and more readable failure reasons.

---

### 2.7 Consolidate ToolResult [x] DONE

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
1. [x] Created canonical `ToolResult` in `cihub/types.py` (11 fields: tool, success, returncode, stdout, stderr, ran, metrics, artifacts, json_data, json_error, report_path)
2. [x] Updated `core/ci_runner/base.py` to import from `types.py` and re-export
3. [x] Updated `commands/hub_ci/__init__.py` to import from `types.py` and re-export
4. [x] Updated `run_tool_with_json_report()` to use unified type with `tool_name` parameter
5. [x] All 2104 tests pass

**Benefit:** One source of truth, easier report merging, AI-consumable outputs.

---

## Part 3: Medium-Priority Improvements

### 3.1 Centralize GitHub Environment Access [x] COMPLETE

**Status:** DONE (2026-01-06)  

**Problem:** 17+ files with direct `os.environ.get("GITHUB_*")` calls.  

**Solution:** Unified `GitHubContext` class that merges:
1. Original `OutputContext` (GITHUB_OUTPUT, GITHUB_STEP_SUMMARY writing)
2. All GITHUB_* environment variable reading

**Implementation:** `cihub/utils/github_context.py`
- 11 GitHub env var fields (repository, ref, ref_name, sha, run_id, run_number, actor, event_name, workspace, workflow_ref, token)
- `from_env()` class method to read from environment
- `from_args()` class method for CLI output config (backward compatible)
- `with_output_config()` to combine env + output config
- Helper properties: `is_ci`, `owner_repo`, `owner`, `repo`, `short_sha`
- Backward compatibility: `OutputContext = GitHubContext` alias

**Tests:** 59 tests in `tests/test_output_context.py` (38 original + 21 new)

**Note:** Scattered env reads can be migrated incrementally as code is touched. The unified `GitHubContext` provides the foundation.

### 3.2 Consolidate RunCI Parameters [x]

**Status:** COMPLETE (2026-01-06)  

**Problem:** `run_ci()` had 10 keyword parameters - too many for clean function signatures.  

**Solution:** Created `RunCIOptions` dataclass in `cihub/services/types.py`:

```python
@dataclass(frozen=True)
class RunCIOptions:
 """Configuration options for run_ci()."""
 output_dir: Path | None = None
 report_path: Path | None = None
 summary_path: Path | None = None
 workdir: str | None = None
 install_deps: bool = False
 no_summary: bool = False
 write_github_summary: bool | None = None
 correlation_id: str | None = None
 config_from_hub: str | None = None
 env: Mapping[str, str] | None = None

 @classmethod
 def from_args(cls, args: Any) -> "RunCIOptions":
 """Create options from argparse namespace."""
 ...
```

**Updated `run_ci()` signature** (`cihub/services/ci_engine/__init__.py`):
```python
def run_ci(
 repo_path: Path,
 *,
 options: RunCIOptions | None = None, # New: pass options object
 output_dir: Path | None = None, # Still works: backward compat kwargs
 # ... other kwargs still accepted for backward compatibility
) -> CiRunResult:
```

**Benefits:**
- Frozen dataclass ensures immutability
- `from_args()` method for CLI integration
- `dataclasses.replace()` for creating modified copies
- Full backward compatibility with existing kwargs

**Updated callers:**
- `cihub/commands/ci.py` now uses `RunCIOptions.from_args(args)`

**Tests:** 11 tests in `tests/test_services_ci.py` cover `RunCIOptions` and `run_ci()` options handling.

**Backward compatibility:** All existing code that passes kwargs directly still works.

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
 CHECK = "check" # Must have: problems
 GENERATE = "generate" # Must have: files_generated or files_modified
 REPORT = "report" # Must have: data
 ACTION = "action" # Must have: summary

@dataclass
class CommandResult:
 exit_code: int
 category: CommandCategory
 summary: str # Now required
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
 lines.append(f" - {problem['message']}")
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

**Status:** DONE (2026-01-15)  

Implemented filesystem and git injection points for tests:

- Added `cihub/utils/filesystem.py` with `FileSystem`, `RealFileSystem`, `MemoryFileSystem`
- Git helpers accept `fs`/`git` abstractions (`get_git_remote`, `get_git_branch`)
- GitHubContext output/summary writes now use the filesystem abstraction
- Tests cover injected filesystem + stub git client usage

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

### 5.1 CLI Re-exporting Helpers [x] COMPLETE (2026-01-06)

**Status:** COMPLETE - Fixed directly instead of phased deprecation.  

**Problem:** `cihub/cli.py` re-exported 50+ functions for backward compatibility, creating messy dependencies.  

**Solution:** Just fixed the imports directly and removed the re-exports.

**Changes:**
1. Updated ~20 test files to import from canonical locations:
 - `CommandResult` → `from cihub.types import CommandResult`
 - `hub_root`, `get_git_branch`, etc. → `from cihub.utils import ...`
 - `render_dispatch_workflow` → `from cihub.services.templates import ...`
 - POM utilities → `from cihub.utils import ...`
2. Removed 50+ re-export lines from `cihub/cli.py`
3. Updated `tests/test_module_structure.py` to verify utilities are NOT exported from cli.py

**Result:** `cli.py` now only exports actual CLI functions (`main`, `build_parser`). All 2234 tests pass.

### 5.2 Mixed Return Types [x] DONE

**Status:** COMPLETE (2026-01-05)  

**Problem (SOLVED):** Some commands returned `int`, others `CommandResult`, requiring CLI to handle both.

**Migration (COMPLETED):**
1. [x] Audited all 47 commands with `-> int | CommandResult:` return type
2. [x] Changed all return types to `-> CommandResult:`
3. [x] Updated `report/__init__.py` summary subcommands to return `CommandResult` instead of `EXIT_SUCCESS`
4. [x] Updated type annotations in: `hub_ci/validation.py` (8), `hub_ci/release.py` (17), `hub_ci/python_tools.py` (3), `hub_ci/security.py` (6), `hub_ci/smoke.py` (4), `hub_ci/java_tools.py` (6), `hub_ci/router.py` (1), `check.py` (1)
5. [x] Fixed test assertions expecting `int` → check `result.exit_code` instead
6. [x] All 2104 tests pass

**Benefit:** CLI now has consistent return types, simpler testing, guaranteed `--json` support.

### 5.3 Special-Case Handling [x] DONE (2026-01-10)

**Issue:** Special cases for tool-specific config extraction and gate evaluation scattered across 3 files.

**Solution Implemented:** Created centralized `ToolAdapter` registry in `cihub/tools/registry.py`:

```python
@dataclass
class ToolAdapter:
    name: str
    language: str
    config_extractor: Callable[[dict, str], dict[str, Any]] | None = None
    gate_keys: list[str] = field(default_factory=list)
    gate_key_defaults: dict[str, bool] = field(default_factory=dict)
    gate_default: bool = True

TOOL_ADAPTERS: dict[tuple[str, str], ToolAdapter] = {
    ("pytest", "python"): ToolAdapter(name="pytest", language="python", config_extractor=_pytest_config),
    ("bandit", "python"): ToolAdapter(name="bandit", language="python",
        gate_keys=["fail_on_high", "fail_on_medium", "fail_on_low"],
        gate_key_defaults={"fail_on_high": True, "fail_on_medium": False, "fail_on_low": False}),
    # ... 20+ adapters for Python and Java tools
}

# Public API
def get_tool_runner_args(config, tool, language) -> dict[str, Any]: ...
def is_tool_gate_enabled(config, tool, language) -> bool: ...
```

**Files Modified:**
- `cihub/tools/registry.py` - Added `ToolAdapter` dataclass and 20+ adapter definitions
- `cihub/services/ci_engine/helpers.py` - `_tool_gate_enabled()` now delegates to registry
- `cihub/services/ci_engine/python_tools.py` - Uses `get_tool_runner_args()` for config extraction
- `cihub/services/ci_engine/java_tools.py` - Uses `get_tool_runner_args()` for config extraction

**Tests Added:** 10 new tests in `tests/test_tool_registry.py::TestToolAdapters`

**Benefits:**
1. Single source of truth for tool-specific config and gate logic
2. Adding new tools only requires adding an adapter entry
3. Per-key defaults for complex gates (e.g., bandit's fail_on_high/medium/low)

### 5.4 CLI Command Sprawl [x] BY DESIGN (Audited 2026-01-05)

**External Review Finding (Gemini Code Review - Grade B+):**

> "This CLI is functional and comprehensive, but it suffers from 'Command Sprawl.' It feels like a Swiss Army Knife where every new blade was bolted onto the handle wherever it fit, rather than being organized into a neat toolbox."

**WARNING: POST-AUDIT UPDATE: The reviewer also identified that this is INTENTIONAL:**

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
 - [x] Safe: Neither is referenced in workflows or UI designs
 - Change: "doctor" → "Check environment readiness"
 - Change: "preflight" → "Alias for doctor (deprecated)"

2. **Phase CLI-2 (Low risk):** Add argparse help groups for better `--help` output
 - [x] Safe: Only affects `--help` display, not command names
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

### Phase 1: Foundation (Current Sprint) [x]
- [x] Create `cihub/core/languages/` structure
- [x] Extract `PythonStrategy` and `JavaStrategy` (delegation pattern)
- [x] Update `run_ci()` to use strategy pattern [x]
- [x] Add tests for strategy selection (33 tests)

### Phase 2: Output Consistency
- [ ] Audit all commands for direct printing
- [ ] Convert to `CommandResult` returns
- [ ] Centralize output in `cli.py`
- [ ] Add renderer abstraction

### Phase 3: Tool Adapters
- [x] Create `cihub/tools/` adapter registry (replaced `core/tools` plan)
- [x] Extract Python tool adapters (registry entries)
- [x] Extract Java tool adapters (registry entries)
- [ ] Centralize subprocess execution

### Phase 4: Polish
- [x] Centralize GitHub env access → **DONE as Part 3.1** (`utils/github_context.py`, 59 tests)
- [x] Consolidate `run_ci()` parameters → **DONE as Part 3.2**
- [x] Add deprecation warnings to CLI re-exports → **DONE as Part 9.1**
- [ ] Documentation updates (ongoing)

---

## Appendix: Files by Refactoring Priority

### Must Touch (High Impact)
| File | Lines | Issue | Status |
|--------------------------------------|---------|-----------------------|--------------------------------------|
| `services/ci_engine/__init__.py` | 179-289 | Language branching | [x] Refactored to use strategy pattern |
| `services/ci_engine/python_tools.py` | 176-198 | Tool dispatch | Strategy delegates here |
| `services/ci_engine/java_tools.py` | 80-103 | Tool dispatch | Strategy delegates here |
| `services/ci_engine/helpers.py` | 104-134 | Duplicate gate config | [x] Uses strategy.get_default_tools() |

### Should Touch (Medium Impact)
| File | Lines | Issue |
|-------------------------------|--------|----------------------|
| `commands/run.py` | 67-89 | Direct printing |
| `commands/detect.py` | 37-48 | Direct printing |
| `commands/hub_ci/__init__.py` | 91-140 | 15+ print statements |
| `services/ci_engine/gates.py` | 26-33 | Scattered env reads |

### Nice to Touch (Low Impact)
| File | Lines | Issue |
|----------------|-------|---------------------------|
| `cli.py` | 13-61 | Re-exports (keep for now) |
| `types.py` | 12-40 | Loose contract |
| `utils/env.py` | - | Add GitHub context |

---

## Part 7: Comprehensive Multi-Agent Audit (2026-01-05)

> **Audit Source:** 6 parallel agents examining CLI, services, core, config, utilities, and hub-ci layers.
> **Methodology:** SOLID principles, DRY analysis, CLI best practices from Real Python and clean-code-python.

### 7.1 CLI Layer Consolidation (HIGH PRIORITY)

#### Finding 7.1.1: Argument Definition Duplication
**Problem:** `--output` and `--github-output` defined repeatedly in `hub_ci.py`.  

**Files:** `cihub/cli_parsers/hub_ci/` lines 29, 71, 84, 107, 124, 141, 153, 165, 192, 218, 262, etc.

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
- Returns `int`: ~46 hub-ci functions (now migrated [x])
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

| Function | Location 1 | Location 2 | Lines |
|-------------------------------|---------------------------|------------------------------|-------|
| `_get_repo_name()` | `report/helpers.py:22-36` | `ci_engine/helpers.py:23-37` | 14 |
| `_detect_java_project_type()` | `report/helpers.py:69-87` | `ci_engine/helpers.py:69-87` | 18 |

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

#### Finding 7.3.3: Ad-hoc Subprocess Calls [x] **DONE**
**Problem:** 30 subprocess.run() calls scattered without consistent patterns.  

**Issues:**
- No standardized timeout (varies: 5, 10, 30, 60, 120 seconds)
- Inconsistent error handling for FileNotFoundError
- Mixed `proc.stdout or proc.stderr` patterns

**COMPLETED (2026-01-06):**

Implemented `safe_run()` wrapper in `cihub/utils/exec_utils.py` with:
- **Timeout constants per ADR-0045:** TIMEOUT_QUICK=30, TIMEOUT_NETWORK=120, TIMEOUT_BUILD=600, TIMEOUT_EXTENDED=900
- **Custom exceptions:** `CommandNotFoundError`, `CommandTimeoutError` for consistent error handling
- **Consistent defaults:** UTF-8 encoding, capture_output=True, text=True

**Migration scope:**
- 34 subprocess.run() calls migrated across 14 files
- Files modified: triage.py, verify.py, check.py, docs.py, preflight.py, secrets.py, templates.py, release.py, python_tools.py, security.py, io.py, helpers.py, git.py (docs_stale), shared.py, hub_ci/__init__.py

**Test coverage:**
- 22 new tests in `tests/test_exec_utils.py`
- Hypothesis property-based tests for edge cases
- All 2200+ tests pass

---

### 7.4 Core Module Refactoring (MEDIUM PRIORITY)

#### Finding 7.4.1: Report Builder Duplication [x] **DONE** (2026-01-10)
**Problem:** `build_python_report()` and `build_java_report()` share 90% code.  

**Files:** `core/ci_report.py:142-256` (Python), `core/ci_report.py:259-381` (Java)

**Solution implemented:**
- Added `ReportMetrics` dataclass capturing language-agnostic shape (43 lines)
- Added `_extract_python_metrics()` for Python tool extraction (80 lines)
- Added `_extract_java_metrics()` for Java tool extraction (87 lines)
- Added `_build_report()` shared report assembly (72 lines)
- Public API unchanged - `build_python_report()` and `build_java_report()` now thin wrappers
- Duplication reduced from ~90% to ~0%; net -16% lines
- All 51 ci_report tests pass

---

#### Finding 7.4.2: resolve_thresholds() SRP Violation [x] **DONE** (2026-01-10)

**Solution implemented:**
- Added `_derive_trivy_fallbacks()` shared helper (13 lines)
- Added `_resolve_python_thresholds()` for Python config extraction (36 lines)
- Added `_resolve_java_thresholds()` for Java config extraction (16 lines)
- Simplified `resolve_thresholds()` from 82 lines to 14-line dispatcher
- All 51 ci_report tests pass

---

#### Finding 7.4.3: Hub-CI Command Surface Is Monolithic [x] **DONE** (2026-01-10)

**Solution implemented:**
- Inventoried all 50 hub-ci subcommands, grouped into 7 families:
  - release (16): actionlint, kyverno, trivy, zizmor, release-*, pytest-summary, summary, enforce
  - validation (11): syntax-check, yamllint, repo-check, source-check, validate-*, verify-*, quarantine-check, enforce-command-result
  - security (6): bandit, pip-audit, security-*
  - java_tools (6): codeql-build, smoke-java-*
  - smoke (4): smoke-python-*
  - python_tools (6): ruff, black, mypy, mutmut, coverage-verify
  - badges (3): badges, badges-commit, outputs
- Router module (`commands/hub_ci/router.py`) was already in place
- Split `cli_parsers/hub_ci.py` (638 lines) into `cli_parsers/hub_ci/` package:
  - `__init__.py`: Orchestrator importing from family modules
  - `validation.py`, `python_tools.py`, `security.py`, `java_tools.py`, `smoke.py`, `badges.py`, `release.py`
- All 2382 tests pass; CLI surface unchanged (verified via `hub-ci --help`)

---

#### Finding 7.4.4: Large CLI Command Handlers (God Modules) [x] **DONE** (2026-01-10)
**Problem:** Several CLI commands bundle parsing, orchestration, rendering, and IO.  

**Files:** `commands/docs.py`, `commands/check.py`, `commands/setup.py`, `commands/verify.py`, `commands/smoke.py`, `commands/secrets.py`, `commands/registry_cmd.py`, `commands/triage_cmd.py`

**Solution implemented:**
- Split large multi-subcommand files into packages
- Assessed remaining files - most are single orchestrators by design

**Completed splits:**
- [x] **docs.py** (858 lines) → `commands/docs/` package:
  - `__init__.py`: Main handlers, `cmd_docs`, `cmd_docs_links` exports (132 lines)
  - `links.py`: Link checking logic - `_check_internal_links`, `_run_lychee` (260 lines)
  - `generate.py`: CLI, config, workflow reference generation (466 lines)
- [x] **registry_cmd.py** (1078 lines) → `commands/registry/` package:
  - `__init__.py`: Router `cmd_registry` + exports
  - `_utils.py`: Shared helper `_derive_hub_root_from_configs_dir`
  - `query.py`: `_cmd_list`, `_cmd_show` (read-only operations)
  - `modify.py`: `_cmd_set`, `_cmd_add`, `_cmd_remove` (modifications)
  - `sync.py`: `_cmd_diff`, `_cmd_sync`, `_cmd_bootstrap` (synchronization)
  - `io.py`: `_cmd_export`, `_cmd_import` (bulk operations)
  - Original `registry_cmd.py` converted to backward-compat shim

**Assessed - no split needed:**
- [x] **triage_cmd.py** (568 lines): Already modularized - imports from 7 submodules (artifacts, github, output, remote, types, verification, watch)
- [x] **check.py** (641 lines): Single orchestrator function, procedural by design
- [x] **setup.py** (556 lines): Single wizard orchestrator with sequential steps, tightly coupled
- [x] **smoke.py** (476 lines): Cohesive test-running logic, single responsibility
- [x] **verify.py** (465 lines): Well-organized validation functions with clear internal structure
- [x] **secrets.py** (426 lines): Two related commands sharing verification helpers

**Future candidates (not blocking, well-organized):**
- **tool_cmd.py** (1262 lines): 22 functions with clear boundaries; could split by operation type if needed
- **profile_cmd.py** (876 lines): 16 functions with CRUD/IO/validate pattern; could split if file grows

**Checklist:**
- [x] Split docs.py and registry_cmd.py into submodules with thin entrypoints
- [x] Assess remaining files - most are single orchestrators by design
- [x] Shared helpers already exist in utils/ modules (no new `_helpers.py` needed)
- [x] Ensure CommandResult + `--json` output stays stable for all subcommands - verified via tests
- [x] All 2382 tests pass

---

#### Finding 7.4.5: Java POM Helpers Mix Parsing + Enforcement [x] **DONE** (2026-01-10)

**Solution implemented:**
- Converted `utils/java_pom.py` (510 lines) to `utils/java_pom/` package
- Created `parse.py`: Pure XML/POM parsing + constants (240 lines)
- Created `rules.py`: Policy/validation with config (150 lines)
- Created `apply.py`: Mutations/writes (145 lines)
- Created `__init__.py`: Re-exports all symbols for backward compatibility
- All 2484 tests pass; imports resolve to new modules

---

#### Finding 7.4.6: Aggregation Runner Duplication [x] **DONE** (2026-01-10)

**Solution implemented:**
- Added `_strip_report_data()` helper (1 line)
- Added `_build_aggregated_report()` shared report builder (24 lines)
- Added `_write_output_files()` for output/summary/details writing (27 lines)
- Added `_check_threshold_violations()` for threshold checking (22 lines)
- Added `_classify_runs()` for pass/fail classification (12 lines)
- Added `_print_summary_banner()` for summary output (38 lines)
- Refactored `run_aggregation()` and `run_reports_aggregation()` to use shared helpers
- Custom formatters preserve original failure message formats
- All 39 aggregation tests + 2481 total tests pass

---

#### Finding 7.4.7: Parser Abstraction Gaps [x] **DONE** (2026-01-10)
**Problem:** Argument wiring is repeated across multiple parser modules despite common helpers.  

**Solution found:** Helpers already exist in `cli_parsers/common.py`:
- 8 factory functions: `add_output_args`, `add_repo_args`, `add_summary_args`, `add_report_args`, `add_path_args`, `add_output_dir_args`, `add_ci_output_args`, `add_tool_runner_args`
- 100+ usages across parser modules

**Assessment (2026-01-10):**
- [x] Helpers exist and are widely adopted
- [x] Remaining manual definitions are legitimate: custom short flags (`-o`), tool-specific defaults (`bandit.json`), or different args (`--repo-count`)
- [x] CLI help output unchanged
- [~] Parser snapshot tests: Deferred - existing CLI help tests cover drift detection

**No further action needed - pattern is established and working.**

---

#### Finding 7.4.8: Missing Core Abstractions [x] **DONE** (2026-01-10)
**Problem:** Command and tool orchestration patterns are duplicated without shared interfaces.  

**Assessment:** Abstractions already exist:
- `CommandHandler` type alias: `Callable[[argparse.Namespace], int | CommandResult]` in `cli_parsers/types.py`
- `ToolResult` unified dataclass: `types.py:46` with consistent contracts
- Tool runner registry: `tools/registry.py` with `get_runner()` and `get_runners()`
- Language strategies: `core/languages/` provides polymorphic tool execution
- `utils/java_pom/` package: Already implements parse → mutate → write pattern

**Checklist:**
- [x] Patterns exist and are working (CommandHandler, ToolResult, language strategies)
- [x] Tool runner registry provides centralized runner lookup
- [x] java_pom package demonstrates BuildFileEditor pattern
- [~] Formal Protocol interfaces: Deferred - current callable/dataclass patterns work well

**No further action needed - abstractions exist and are consistently used.**

---

### 7.5 Config/Schema Consistency (MEDIUM PRIORITY)

#### Finding 7.5.1: Schema Validation Bypass
**Problem:** Hub-CI config loading skips schema validation.  

**File:** `commands/hub_ci/__init__.py:90-97`
```python
def _load_config(path: Path | None) -> dict[str, Any]:
 return normalize_config(load_yaml_file(path)) # NO validate_config()!
```

**Risk:** Invalid configs silently proceed.

**Fix:** Call `validate_config()` after `normalize_config()`.

---

#### Finding 7.5.2: Defaults Defined in 4 Places
**Problem:** `fail_on_cvss=7` default in multiple files.  

| Location | Line | Value |
|-----------------------------------------|----------|---------------------------|
| `cihub/data/schema/ci-hub-config.schema.json` | 249, 342 | `"default": 7` |
| `cihub/config/fallbacks.py` | 15, 47 | `"fail_on_cvss": 7` |
| `cihub/config/loader/inputs.py` | 59, 95 | `.get("fail_on_cvss", 7)` |
| `cihub/commands/config_outputs.py` | 107, 118 | `.get("fail_on_cvss", 7)` |

**Risk:** Changing default requires 4-file update.

**Fix:** Define constants module or use schema as single source.

---

#### Finding 7.5.3: Inconsistent `fail_on_*` Naming [x] **DONE** (2026-01-15)

**Problem:** Tool configs use multiple `fail_on_*` variants with overlapping semantics.  

**Examples:** `fail_on_error`, `fail_on_issues`, `fail_on_violation`, `fail_on_format_issues`, `fail_on_vuln`, `fail_on_critical`, `fail_on_high`

**Risk:** Harder schema validation and inconsistent UX across tools.

**Solution Implemented:**
- Added `get_fail_on_flag()` and `get_fail_on_cvss()` helpers in `cihub/config/normalize.py`
- Defined `_FAIL_ON_KEY_MAP` for tool → canonical flag mapping
- Defined `_FAIL_ON_DEFAULTS` and `_TOOL_FAIL_ON_DEFAULTS` for schema-aligned defaults
- Added 55 tests in `tests/test_fail_on_normalization.py` including schema-code alignment tests
- Added ADR-0052 documenting the normalization pattern

**Checklist:**
- [x] Inventory all `fail_on_*` fields in schema + config defaults.
- [x] Define canonical naming rules and add normalization/aliases.
- [x] Add schema tests to prevent new variants.
- [x] Update docs/reference generation accordingly (ADR-0052 added).

---

### 7.6 Services Layer (MEDIUM PRIORITY)

#### Finding 7.6.1: run_ci() God Method [~] **PARTIAL** (2026-01-10)

**Problem:** 300+ line function handling 7 responsibilities.  

**File:** `services/ci_engine/__init__.py:132-467`

**Progress:**
- [x] Self-validation extracted to `validation.py::_self_validate_report()` (55 lines → 1 line call)
- [~] Strategy pattern already delegates: tool execution, report building, gate evaluation
- [~] Remaining blocks are tightly coupled to return values (output writing)

**Status:** Function reduced from ~335 to ~280 lines. Further extraction of output writing would require complex return types. Strategy pattern handles most responsibilities - remaining code is orchestration glue that's reasonable to keep inline.  

---

#### Finding 7.6.2: Hardcoded Tool Runner Imports [x] **DONE** (2026-01-10)

**Problem:** 19 individual tool runners imported directly.  

**Solution Implemented:**
- Added `get_runner(tool, language)` and `get_runners(language)` to `cihub/tools/registry.py`
- Lazy-loaded runner functions via `_load_python_runners()` and `_load_java_runners()` (cached)
- Updated `PythonStrategy.get_runners()` and `JavaStrategy.get_runners()` to use centralized registry
- Updated `ci_engine/__init__.py` to use `__getattr__` for backward-compat PYTHON_RUNNERS/JAVA_RUNNERS
- Removed 19 direct runner imports from ci_engine/__init__.py (now only imports `run_java_build` for re-export)

**Files Modified:**
- `cihub/tools/registry.py` - Added runner registry section (~70 lines)
- `cihub/core/languages/python.py` - Simplified get_runners() to 1 line
- `cihub/core/languages/java.py` - Simplified get_runners() to 1 line
- `cihub/services/ci_engine/__init__.py` - Removed 19 imports, added __getattr__

---

#### Finding 7.6.3: Registry Service God Module [x] **DONE** (2026-01-11)
**Problem:** Registry service handles IO, normalization, diffing, and sync in one file.  

**Solution implemented:** Split `services/registry_service.py` (1592 lines) → `services/registry/` package:

| Module | Lines | Functions |
|--------|-------|-----------|
| `__init__.py` | 109 | Re-exports all public functions |
| `_paths.py` | 42 | Path utilities with monkeypatch compat |
| `io.py` | 52 | `load_registry`, `save_registry` |
| `normalize.py` | 73 | `_normalize_*` functions |
| `thresholds.py` | 145 | Threshold value computation |
| `diff.py` | 611 | `compute_diff` and helpers |
| `sync.py` | 532 | `sync_to_configs`, `bootstrap_from_configs` |
| `query.py` | 261 | `list_repos`, `get_repo_config`, setters |

- Original `registry_service.py` → 92-line backward-compat shim
- All 48 registry tests pass; 2534 total tests pass

---

#### Finding 7.6.4: Triage/Report Pipeline Monolith [x] **DONE** (already modularized)
**Problem:** Triage + report validation logic is bundled in large service modules.  

**Assessment:** Already modularized - marked as "reference pattern" in Part 1.5:

- `commands/triage/` (9 modules): artifacts, github, log_parser, output, remote, types, verification, watch
- `services/triage/` (4 modules): detection, evidence, types, __init__
- `triage_service.py` now only 614 lines (thin orchestrator)
- `report_validator/` package: schema/content/artifact/types validators (modular)

**No further action needed - triage is the reference pattern for modularization.**

---

### 7.7 Test Coverage Gaps (MEDIUM PRIORITY)

#### Finding 7.7.1: High-LOC Modules Need Focused Tests [x] **DONE** (2026-01-11)
**Problem:** Several large modules rely on broad integration tests instead of focused unit coverage.  

**Assessment:** Coverage is good across target modules:

| Module | Tests | Notes |
|--------|-------|-------|
| hub_ci | 62 | Good coverage |
| docs | 114 | Excellent coverage |
| check | 8 | Thin orchestrator - calls well-tested commands |
| registry | 98 | Excellent coverage |
| triage | 96 | Excellent coverage |
| pom | 79 | Good coverage (in test_pom_parsing.py) |
| aggregation | 39 | Good coverage |

**Total: 2534+ tests in suite.** No additional tests needed - coverage is comprehensive.

---

## Part 8: Updated Implementation Roadmap

### Phase 1: Foundation [x] COMPLETE
- [x] Language strategies (Python/Java)
- [x] Hub-CI CommandResult migration (**46/46 functions**) [x]
- [x] Gate spec wiring (26 thresholds)
- [x] Triage modularization (reference pattern)
- [x] CommandResult helpers (`result_ok`, `result_fail`, `run_and_capture`)
- [x] Strategy kwargs filtering (`get_allowed_kwargs()`)
- [x] Strategy virtual tools (`get_virtual_tools()`)
- [x] Strategy docker config encapsulation (`get_docker_config()`)

### Phase 2: Consolidation Helpers (HIGH PRIORITY)
- [x] Create `cli_parsers/common.py` with `add_output_args()`, `add_summary_args()` [x] (2026-01-05)
 - 8 factory functions: `add_output_args`, `add_summary_args`, `add_repo_args`, `add_report_args`, `add_path_args`, `add_output_dir_args`, `add_ci_output_args`, `add_tool_runner_args`
 - `hub_ci.py`: 628 → 535 lines (93 lines saved)
 - `report.py` and `core.py` also refactored
 - 30 parameterized tests in `test_cli_common.py`
- [x] Create `cihub/utils/github_context.py` with `OutputContext` dataclass and **migrate all 32 call sites** [x] (2026-01-05)
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
- [x] Add `hub_ci/__init__.py` tool execution helpers [x] (2026-01-05)
 - `ToolResult` dataclass: structured result from tool execution
 - `ensure_executable(path)`: consolidates 6 chmod patterns
 - `load_json_report(path, default)`: consolidates 15+ JSON parse patterns
 - `run_tool_with_json_report(cmd, cwd, report_path)`: full tool execution + JSON parsing
 - 39 tests in `tests/test_tool_helpers.py` (parameterized + Hypothesis property-based)
- [x] Consolidate `_get_repo_name()`, `_detect_java_project_type()` to `cihub/utils/project.py` [x] (2026-01-05)
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

### Phase 3: Output Consistency - Infrastructure Complete, Migration In Progress
- [x] Audit 263+ print() calls in 37 command files [x] (audit completed 2026-01-05)
- [x] Implement OutputRenderer abstraction (Part 4.1 approach - smarter than utils/output.py) [x] (2026-01-05)
 - Created `cihub/output/` package with:
 - `__init__.py` - Clean exports
 - `renderers.py` - OutputRenderer ABC, HumanRenderer, JsonRenderer
 - HumanRenderer contains ALL formatting logic (tables, lists, key-values, problems)
 - JsonRenderer uses CommandResult.to_payload() for consistent JSON
 - `get_renderer(json_mode)` factory function
- [x] Centralize output rendering in `cli.py` [x]
 - cli.py now uses `get_renderer()` at lines 394-400
 - Single point of output: `renderer.render(result, command, duration_ms)`
- [x] 35 tests in `tests/test_output_renderers.py` (parameterized + 5 Hypothesis property-based)
- [x] Contract enforcement test (`test_command_output_contract.py`) - prevents regression
- **Architecture:** Commands return CommandResult with data, renderers decide how to display

**Command Migration Progress (2026-01-05):**
| File | Prints Removed | Status |
|------|---------------|--------|
| adr.py | 16 | [x] Migrated |
| triage.py | 34 | [x] Migrated |
| secrets.py | 32 | [x] Migrated |
| templates.py | 22 | [x] Migrated |
| pom.py | 21 | [x] Migrated |
| dispatch.py | 10 | [x] Migrated |
| config_cmd.py | 9 | [x] Migrated |
| update.py | 8 | [x] Migrated |
| docs.py | 10 | [x] Migrated |
| new.py | 10 | [x] Migrated |
| init.py | 10 | [x] Migrated |
| smoke.py | 8 | [x] Migrated |
| discover.py | 8 | [x] Migrated |
| validate.py | 7 | [x] Migrated **NEW** |
| detect.py | 3 | [x] Migrated **NEW** |
| **Total migrated** | **~208** | **15 files** |
| **Remaining** | **~55** | **~7 files + report/ subpkg** |

### Phase 4: Utilities Consolidation
- [x] Create `cihub/utils/github_env.py` with GitHubEnv dataclass → **DONE as `github_context.py`** (Part 3.1)
- [x] Extend `cihub/utils/exec_utils.py` with `safe_run()` wrapper → **DONE as Part 7.3.3** (34 migrations)
- [ ] Create `cihub/utils/json_io.py` with `load_json_files()` (deferred - not critical)
- [x] Replace 51 direct `os.environ.get()` calls with utility functions → **Partial via GitHubContext** (11 env vars centralized)

### Phase 5: Config/Schema Alignment
- [ ] Add `validate_config()` call to hub_ci._load_config()
- [ ] Define `cihub/config/constants.py` for shared defaults
- [ ] Call `check_threshold_sanity()` during normal config load
- [ ] Document effective-only thresholds vs configurable

### Phase 6: Core Refactoring
- [x] Extract common report builder template from Python/Java functions (2026-01-10: `_build_report()` + `ReportMetrics` dataclass in ci_report.py)
- [x] Move `resolve_thresholds()` into LanguageStrategy (2026-01-10: `PythonStrategy.resolve_thresholds()`, `JavaStrategy.resolve_thresholds()`)
- [ ] Create `cihub/utils/severity.py` with `count_severities()` helper
- [x] Add TypedDict or dataclass for report structure (2026-01-10: `ReportMetrics` dataclass)

### Phase 7: Services Simplification
- [x] Split `run_ci()` into 5 focused orchestrator functions (BY DESIGN: uses Strategy pattern, already well-structured)
- [x] Implement tool runner registry pattern (2026-01-10: `cihub/tools/registry.py` with get_runners(), get_runner())
- [x] Split report_validator into schema/content/artifact validators (2026-01-15: `cihub/services/report_validator/` package with types.py, schema.py, artifact.py, content.py)

---

## Appendix B: New Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `cli_parsers/common.py` | **CREATED** [x] - 8 argument factories | High |
| `utils/github_context.py` | **CREATED** [x] - OutputContext dataclass (32 call sites migrated) | High |
| `utils/github_env.py` | GitHub env dataclass (extend github_context.py instead) | Medium |
| `utils/exec_utils.py` | **EXISTS** - add `safe_run()` | High |
| `utils/json_io.py` | JSON file operations | Medium |
| `utils/severity.py` | Severity counting | Medium |
| `output/__init__.py` | **CREATED** [x] - OutputRenderer exports | High |
| `output/renderers.py` | **CREATED** [x] - HumanRenderer, JsonRenderer (35 tests) | High |
| `config/constants.py` | Shared default values | Medium |
| `tools/registry.py` | Tool runner registry | Medium |

---

## Appendix C: Quick Wins (< 1 hour each)

1. ~~**Create `add_output_args()`**~~ [x] DONE - Eliminated 36+ duplicate arg definitions
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

| Environment | Black/isort Status |
|---------------|------------------------------------------------------|
| CI workflows | [x] `run_black`, `run_isort` toggles work |
| `cihub check` | [ ] Line 328: "Black removed - using Ruff format only" |
| Makefile | [ ] Only `ruff format`, no black/isort targets |

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
 files: '^cihub/data/config/.*\\.yaml$'
 args: ['--schemafile=cihub/data/schema/ci-hub-config.schema.json']
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

### 9.3 Schema Consolidation [x] DONE

**Status:** COMPLETE (2026-01-05)  

**Problem (SOLVED):** Schema duplication causing ~150 lines of redundant definitions.

**Migration (COMPLETED):**
1. [x] Added `sharedSbomTool` and `sharedSemgrepTool` to `#/definitions` in ci-hub-config.schema.json
2. [x] Updated `javaTools.sbom` and `javaTools.semgrep` to use `$ref`
3. [x] Updated `pythonTools.sbom` and `pythonTools.semgrep` to use `$ref`
4. [x] Added `toolStatusMap` definition to ci-report.v2.json
5. [x] Updated `tools_ran`, `tools_configured`, `tools_success`, `tools_require_run` to use `$ref`
6. [x] Fixed `test_tools_ran_schema_covers_all_tools` to follow `$ref`
7. [x] All 2104 tests pass

**Benefit:** ~100 lines removed, single source of truth for tool definitions, easier maintenance.

**Note:** docker, trivy, codeql remain inline because they have language-specific defaults (e.g., `languages: ["java"]` vs `["python"]`).

#### Finding 9.3.1: Shared Tools Duplicated (RESOLVED)
**Problem:** 5 tools defined identically in javaTools AND pythonTools.  

| Tool | Duplicate Lines | Status |
|---------|-----------------|--------|
| docker | 34 | WARNING: Different defaults (has `dockerfile` in Java) |
| trivy | 30 | WARNING: Different defaults (Java has `fail_on_cvss`) |
| codeql | 28 | WARNING: Different defaults (`languages` differs) |
| sbom | 26 | [x] EXTRACTED to `sharedSbomTool` |
| semgrep | 28 | [x] EXTRACTED to `sharedSemgrepTool` |

**Fix:** Extracted identical tools (sbom, semgrep) to `#/definitions/sharedTools` (~54 lines removed)

---

#### Finding 9.3.2: Triple Default Definition
**Problem:** Same defaults in 3 places.  

| Source | File |
|--------|---------------------------------------------|
| Schema | `cihub/data/schema/ci-hub-config.schema.json` |
| YAML | `cihub/data/config/defaults.yaml` |
| Python | `cihub/config/fallbacks.py` |

**Fix:** Generate YAML and Python FROM schema (single source of truth).

---

#### Finding 9.3.3: Report Schema Tool Lists (RESOLVED)
**Problem:** 4 identical 22-tool lists in `ci-report.v2.json`.  

**Fix:** [x] Extracted to `#/definitions/toolStatusMap`, referenced 4x (~66 lines removed).

---

#### Finding 9.3.4: Optional Features Unvalidated
**Problem:** `canary`, `chaos`, etc. have `additionalProperties: true`.  

**Fix:** Create full schema definitions for each optional feature.

---

### 9.4 Implementation Phases

#### Phase 1: Scripts & Tooling (Immediate)
- [x] Remove deprecated script entry points from pyproject.toml [x] 2026-01-05
- [x] Set removal date for 11 script shims [x] 2026-01-05 (removal: 2026-02-01)
- [x] Add black/isort to `cihub check` (match CI parity) [x] 2026-01-05
- [x] Add `format-black`, `format-isort`, `format-all` Makefile targets [x] 2026-01-05
- [x] Add JSON schema validation to pre-commit [x] 2026-01-06 (check-jsonschema hook)

#### Phase 2: Workflow Security [x] COMPLETE (2026-01-06)
- [x] Add harden-runner to 14 workflows [x] 2026-01-06 (configurable via `harden_runner_policy` input)
- [x] Verify action pinning is consistent [x] (all pinned to SHAs)

#### Phase 3: Schema Consolidation [x] COMPLETE (2026-01-05)
- [x] Extract `sharedTools` definition (sbom, semgrep)
- [x] Extract `toolStatusMap` definition (22-tool boolean map)
- [ ] Add full schemas for optional features (DEFERRED - low priority)

#### Phase 4: Config Generation (2-3 days)
- [x] Script to generate `defaults.yaml` from schema [x] 2026-01-15
- [x] Script to generate `fallbacks.py` from schema [x] 2026-01-15
- [x] Add CI check for schema-defaults alignment [x] 2026-01-15

---

### 9.5 Industry Best Practices Checklist

| Practice | Status | Action |
|----------------------------|--------|---------------------------------------------|
| Trunk-based development | [x] | Already using |
| Multiple formatter support | [x] | CI has black/isort; local tooling updated [x] |
| Action pinning | [x] | All pinned to SHAs |
| Pre-commit automation | [x] | JSON schema validation added (2026-01-06) |
| Explicit workflows | [x] | Boolean-toggle architecture preserved |
| Single source of truth | [x] | Schema-derived defaults + fallbacks generated |
| Pydantic validation | [ ] | Consider for config types |
| Security hardening | [x] | harden-runner added to 14 workflows (2026-01-06) |

**2026-01-06 Automation Audit Summary (UPDATED):**
- **14 workflows** [x] security hardened with harden-runner (configurable toggle)
- **11 deprecated scripts** ready for removal (deprecation warnings added)
- **~400 lines** of schema duplication (partial: sharedTools extracted)
- **Triple default definition** problem (partial: working toward single source)
- **Local/CI parity** [x] black/isort added to `cihub check` and Makefile
- **Pre-commit** [x] JSON schema validation added

---

## Part 10: Testing Improvements (2026-01-05)

> **Audit Source:** Analysis of test patterns + research on pytest best practices.
> **Research:** [Pytest Parameterized Tests](https://pytest-with-eric.com/introduction/pytest-parameterized-tests/), [Hypothesis Property-Based Testing](https://pytest-with-eric.com/pytest-advanced/hypothesis-testing-python/), [Python Testing Frameworks 2025](https://www.geeksforgeeks.org/python/best-python-testing-frameworks/), [Mutation Testing Guide](https://mastersoftwaretesting.com/testing-fundamentals/types-of-testing/mutation-testing)

### 10.1 Current Testing State

| Metric | Current | Opportunity |
|----------------------------------|---------------------|---------------------------|
| Test files | 70 | - |
| `@pytest.mark.parametrize` usage | 25 uses in 6 files | Expand to 30+ files |
| `@pytest.fixture` usage | 68 uses in 18 files | Centralize in conftest.py |
| Hypothesis (property-based) | 25 uses in 5 files | Expand to critical paths |
| Mutmut (mutation testing) | [x] Configured | Already integrated |
| conftest.py | [ ] Missing | Create shared fixtures |
| pytest-xdist (parallel) | [ ] Missing | Add for faster CI |

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

| Test File | Current Tests | Parameterize Opportunity |
|-------------------------|-----------------------|--------------------------|
| `test_config_module.py` | Individual tool tests | All tool configs |
| `test_ci_report.py` | Python/Java separate | Language matrix |
| `test_services_ci.py` | Individual services | Service operations |
| `test_hub_ci.py` | Per-command tests | Command matrix |
| `test_cli_commands.py` | Per-command tests | CLI subcommands |

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

| Module | Property to Test |
|--------------------------------|-------------------------------------------------|
| `config/normalize.py` | Threshold profiles always produce valid configs |
| `config/schema.py` | Any valid config passes validation |
| `core/ci_report.py` | Report builder handles any tool combination |
| `core/gate_specs.py` | Gates evaluate consistently for boundary values |
| `services/report_validator/` | Validator catches all invalid reports |

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
 "pytest-xdist>=3.0", # Parallel test execution
]

[tool.pytest.ini_options]
addopts = "-n auto" # Auto-detect CPU cores
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
- [x] Create `tests/conftest.py` with shared fixtures [x] 2026-01-05
- [x] Add `pytest-xdist` for parallel execution [x] 2026-01-05
- [x] Add `hypothesis` to dev dependencies [x] 2026-01-05
- [x] Identify 10 test files for parameterization [x] 2026-01-05

#### Phase T2: Parameterization (1-2 days)
- [x] Refactor `test_config_module.py` with PathConfig matrix [x] 2026-01-05
- [x] Refactor `test_ci_engine.py` with Java project type matrix [x] 2026-01-05
- [x] Refactor `test_hub_ci.py` with command matrix [x] 2026-01-05
- [x] Refactor `test_language_strategies.py` with strategy matrix [x] 2026-01-05
- [x] Refactor `test_cihub_cli.py` with subcommand matrix [x] 2026-01-05

#### Phase T3: Property-Based Testing (1-2 days)
- [x] Create `tests/test_property_based.py` with Hypothesis [x] 2026-01-05
- [x] Add Hypothesis tests for deep_merge properties [x] 2026-01-05
- [x] Add Hypothesis tests for threshold boundaries [x] 2026-01-05
- [x] Add Hypothesis tests for tool config properties [x] 2026-01-05
- [x] Add Hypothesis tests for report structure invariants [x] 2026-01-05

#### Phase T4: Integration (Ongoing)
- [ ] Run parameterized tests with each PR
- [~] Track mutation testing scores (baseline run completes: 4475 mutants, ~51% score; CI CLI adapter tests added; per-module baselines pending - see TEST_REORGANIZATION.md)
- [ ] Add contract tests as services grow

---

### 10.4 Testing Best Practices Checklist

| Practice | Status | Action |
|-------------------------------|--------|-------------------------------|
| Shared fixtures (conftest.py) | [x] | Created `tests/conftest.py` [x] |
| Parameterized tests | WARNING: | Expand from 6 to 30+ files |
| Property-based (Hypothesis) | WARNING: | Expand from 5 to 15+ files |
| Mutation testing (mutmut) | [x] | Already configured |
| Parallel execution (xdist) | [x] | Added `pytest-xdist>=3.0` [x] |
| Coverage gates | [x] | 70% minimum enforced |
| Snapshot testing | WARNING: | Have some, could expand |

**2026-01-05 Testing Audit Summary:**
- **70 test files** with room for consolidation
- ~~Parameterized testing underutilized (6/70 files)~~ → Now 10+ files with parameterized tests [x]
- ~~Hypothesis underutilized (5/70 files)~~ → Added `test_property_based.py` with 12 tests [x]
- ~~No conftest.py~~ → Created `tests/conftest.py` [x]
- ~~pytest-xdist missing~~ → Added to dev dependencies [x]

**Refactored Test Files (2026-01-05):**
- `test_config_module.py`: PathConfig matrix (8 tests → 2 parameterized)
- `test_ci_engine.py`: Java project type matrix (6 tests → 1 parameterized)
- `test_hub_ci.py`: TestExtractCount, TestCountPipAuditVulns, TestResolveOutputPath, TestCmdZizmorCheck
- `test_language_strategies.py`: TestStrategyCommonBehavior, TestStrategyDetection, TestJavaBuildToolDetection
- `test_cihub_cli.py`: TestSafeUrlopen (URL schemes), TestMainFunction (JSON output, info flags)
- `test_output_context.py`: **NEW** 38 tests for OutputContext (parameterized + Hypothesis property-based)
- `test_tool_helpers.py`: **NEW** 39 tests for ToolResult, ensure_executable, load_json_report, run_tool_with_json_report
- `test_utils_project.py`: **NEW** 37 tests for get_repo_name, detect_java_project_type (parameterized + integration + 6 Hypothesis property-based)
