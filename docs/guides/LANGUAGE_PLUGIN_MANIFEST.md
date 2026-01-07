# Language Plugin Manifest

**Purpose:** This document provides AI assistants with complete context to add new language support to CIHub.

**Usage:** When a user requests adding a new language (e.g., JavaScript, Go, Rust), an AI can use this manifest to generate all required code, following the established patterns.

---

## Architecture Overview

CIHub uses a **Language Strategy Pattern** (see ADR-0041) that encapsulates all language-specific CI behavior. Each language is represented by a single strategy class that implements the `LanguageStrategy` abstract base class.

```
┌─────────────────────────────────────────────────────────────────┐
│                         CI Engine                                │
│  (Language-agnostic orchestration - does NOT change)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Language Strategy Registry                    │
│  get_strategy("python") → PythonStrategy                        │
│  get_strategy("java")   → JavaStrategy                          │
│  get_strategy("javascript") → JavaScriptStrategy (NEW)          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ PythonStrategy│     │ JavaStrategy │     │ JSStrategy   │
│              │     │              │     │   (NEW)      │
│ - 14 tools   │     │ - 12 tools   │     │ - N tools    │
│ - runners    │     │ - runners    │     │ - runners    │
│ - gates      │     │ - gates      │     │ - gates      │
│ - thresholds │     │ - thresholds │     │ - thresholds │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## Files Required to Add a New Language

### TIER 1: Core Implementation (REQUIRED)

| File | Action | Description |
|------|--------|-------------|
| `cihub/core/languages/{lang}.py` | **CREATE** | Strategy class implementing LanguageStrategy |
| `cihub/core/languages/registry.py` | **MODIFY** | Add one line to register the new strategy |
| `cihub/tools/registry.py` | **MODIFY** | Add {LANG}_TOOLS list |
| `schema/ci-hub-config.schema.json` | **MODIFY** | Add language to enum, add {lang}.tools section |

### TIER 2: Tool Runners (REQUIRED)

| File | Action | Description |
|------|--------|-------------|
| `cihub/services/ci_engine/{lang}_tools.py` | **CREATE** | Tool runner functions |
| `cihub/services/ci_engine/gates.py` | **MODIFY** | Add `_evaluate_{lang}_gates()` function |

### TIER 3: Reports & Config (REQUIRED)

| File | Action | Description |
|------|--------|-------------|
| `cihub/core/ci_report.py` | **MODIFY** | Add `build_{lang}_report()` function |
| `config/defaults.yaml` | **MODIFY** | Add {lang} defaults section |

### TIER 4: Templates (OPTIONAL but recommended)

| File | Action | Description |
|------|--------|-------------|
| `templates/profiles/{lang}-quality.yaml` | **CREATE** | Quality-focused profile |
| `templates/profiles/{lang}-minimal.yaml` | **CREATE** | Minimal CI profile |

### TIER 5: Testing (REQUIRED)

| File | Action | Description |
|------|--------|-------------|
| `tests/test_{lang}_strategy.py` | **CREATE** | Strategy unit tests |
| `tests/fixtures/{lang}/` | **CREATE** | Test fixture directory |

---

## LanguageStrategy Abstract Base Class

**Location:** `cihub/core/languages/base.py`

### Required Methods (MUST implement)

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

class LanguageStrategy(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Return language identifier (e.g., 'python', 'javascript')"""
        pass

    @abstractmethod
    def get_runners(self) -> dict[str, Callable[..., Any]]:
        """Return map of tool names to runner functions.
        Example: {'jest': run_jest, 'eslint': run_eslint}
        NOTE: Excludes virtual tools (those without actual runners)
        """
        pass

    @abstractmethod
    def get_default_tools(self) -> list[str]:
        """Return ALL tools for this language (including virtual tools).
        Example: ['jest', 'eslint', 'prettier', 'npm_audit']
        """
        pass

    @abstractmethod
    def get_thresholds(self) -> tuple[ThresholdSpec, ...]:
        """Return threshold specifications for quality gates.
        Example: (
            ThresholdSpec('Min Coverage', 'coverage_min', '%', Comparator.GTE, 'coverage', '...'),
            ThresholdSpec('Max ESLint Errors', 'max_eslint_errors', '', Comparator.LTE, 'eslint_errors', '...'),
        )
        """
        pass

    @abstractmethod
    def get_tool_specs(self) -> tuple[ToolSpec, ...]:
        """Return tool specifications with categories.
        Example: (
            ToolSpec(Category.TESTING, 'jest', 'jest'),
            ToolSpec(Category.LINTING, 'eslint', 'eslint'),
        )
        """
        pass

    @abstractmethod
    def run_tools(
        self,
        config: dict[str, Any],
        repo_path: Path,
        workdir: str,
        output_dir: Path,
        problems: list[dict[str, Any]],
        **kwargs,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
        """Execute all enabled tools.
        Returns: (tool_outputs, tools_ran, tools_success)
        """
        pass

    @abstractmethod
    def evaluate_gates(
        self,
        report: dict[str, Any],
        thresholds: dict[str, Any],
        tools_configured: dict[str, bool],
        config: dict[str, Any],
    ) -> list[str]:
        """Evaluate quality gates based on tool results.
        Returns: List of failure messages (empty if all gates pass)
        """
        pass

    @abstractmethod
    def resolve_thresholds(self, config: dict[str, Any]) -> dict[str, Any]:
        """Extract threshold values from config.
        Returns: Dict like {'coverage_min': 80, 'max_eslint_errors': 0}
        """
        pass
```

### Optional Methods (CAN override)

```python
    def detect(self, repo_path: Path) -> float:
        """Auto-detect if this language applies to a repo.
        Returns: Confidence score 0.0 to 1.0
        Default: 0.0 (no detection)
        """
        return 0.0

    def get_virtual_tools(self) -> list[str]:
        """Return tools tracked in reports but without runners.
        Example: ['codeql'] (run separately in GitHub Actions)
        """
        return []

    def get_allowed_kwargs(self) -> frozenset[str]:
        """Return which kwargs run_tools() accepts.
        Example: frozenset({'install_deps'})
        """
        return frozenset()

    def get_docker_compose_default(self) -> str | None:
        """Default docker-compose filename for this language."""
        return None

    def get_context_extras(self, config: dict, workdir_path: Path) -> dict[str, Any]:
        """Return extra context for reports.
        Example: {'package_manager': 'npm'}
        """
        return {}
```

---

## Example: JavaScript Strategy Implementation

```python
# cihub/core/languages/javascript.py
"""JavaScript/TypeScript language strategy for CIHub."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from cihub.core.gate_specs import Category, Comparator, ThresholdSpec, ToolSpec
from cihub.core.languages.base import LanguageStrategy
from cihub.tools.registry import JAVASCRIPT_TOOLS

if TYPE_CHECKING:
    pass


class JavaScriptStrategy(LanguageStrategy):
    """Strategy for JavaScript/TypeScript projects."""

    @property
    def name(self) -> str:
        return "javascript"

    def detect(self, repo_path: Path) -> float:
        """Detect JavaScript/TypeScript projects."""
        if (repo_path / "package.json").exists():
            return 0.9
        if (repo_path / "tsconfig.json").exists():
            return 0.85
        if any(repo_path.glob("*.js")) or any(repo_path.glob("*.ts")):
            return 0.5
        return 0.0

    def get_runners(self) -> dict[str, Callable[..., Any]]:
        """Map tool names to runner functions."""
        from cihub.services.ci_engine.javascript_tools import (
            run_eslint,
            run_jest,
            run_npm_audit,
            run_prettier,
            run_sbom,
            run_semgrep,
            run_trivy,
            run_tsc,
        )

        return {
            "jest": run_jest,
            "eslint": run_eslint,
            "prettier": run_prettier,
            "tsc": run_tsc,
            "npm_audit": run_npm_audit,
            "sbom": run_sbom,
            "semgrep": run_semgrep,
            "trivy": run_trivy,
        }

    def get_default_tools(self) -> list[str]:
        """Return all JavaScript tools."""
        return list(JAVASCRIPT_TOOLS)

    def get_virtual_tools(self) -> list[str]:
        """Tools tracked but run externally."""
        return ["codeql"]

    def get_thresholds(self) -> tuple[ThresholdSpec, ...]:
        """JavaScript-specific thresholds."""
        return (
            ThresholdSpec(
                label="Min Coverage",
                key="coverage_min",
                unit="%",
                comparator=Comparator.GTE,
                metric_key="coverage",
                failure_template="coverage {value}% < {threshold}%",
            ),
            ThresholdSpec(
                label="Max ESLint Errors",
                key="max_eslint_errors",
                unit="",
                comparator=Comparator.LTE,
                metric_key="eslint_errors",
                failure_template="eslint errors {value} > {threshold}",
            ),
            ThresholdSpec(
                label="Max npm Audit Vulns",
                key="max_npm_audit_vulns",
                unit="",
                comparator=Comparator.LTE,
                metric_key="npm_audit_vulns",
                failure_template="npm audit vulnerabilities {value} > {threshold}",
            ),
        )

    def get_tool_specs(self) -> tuple[ToolSpec, ...]:
        """Tool specifications for JavaScript."""
        return (
            ToolSpec(Category.TESTING, "jest", "jest"),
            ToolSpec(Category.LINTING, "eslint", "eslint"),
            ToolSpec(Category.LINTING, "prettier", "prettier"),
            ToolSpec(Category.LINTING, "tsc", "tsc"),
            ToolSpec(Category.SECURITY, "npm_audit", "npm_audit"),
            ToolSpec(Category.SECURITY, "semgrep", "semgrep"),
            ToolSpec(Category.SECURITY, "trivy", "trivy"),
            ToolSpec(Category.SECURITY, "codeql", "codeql"),
            ToolSpec(Category.CONTAINER, "sbom", "sbom"),
        )

    def get_allowed_kwargs(self) -> frozenset[str]:
        """Allowed kwargs for run_tools."""
        return frozenset({"install_deps", "package_manager"})

    def run_tools(
        self,
        config: dict[str, Any],
        repo_path: Path,
        workdir: str,
        output_dir: Path,
        problems: list[dict[str, Any]],
        **kwargs,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
        """Run JavaScript tools."""
        from cihub.services.ci_engine.javascript_tools import _run_javascript_tools

        return _run_javascript_tools(
            config=config,
            repo_path=repo_path,
            workdir=workdir,
            output_dir=output_dir,
            problems=problems,
            **kwargs,
        )

    def evaluate_gates(
        self,
        report: dict[str, Any],
        thresholds: dict[str, Any],
        tools_configured: dict[str, bool],
        config: dict[str, Any],
    ) -> list[str]:
        """Evaluate JavaScript quality gates."""
        from cihub.services.ci_engine.gates import _evaluate_javascript_gates

        return _evaluate_javascript_gates(report, thresholds, tools_configured, config)

    def resolve_thresholds(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve threshold values from config."""
        from cihub.services.ci_engine.thresholds import resolve_thresholds

        return resolve_thresholds(config, "javascript")

    def build_report(
        self,
        config: dict[str, Any],
        tool_outputs: dict[str, dict[str, Any]],
        tools_configured: dict[str, bool],
        tools_ran: dict[str, bool],
        tools_success: dict[str, bool],
        thresholds: dict[str, Any],
        context: dict[str, Any],
        *,
        tools_require_run: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Build JavaScript CI report."""
        from cihub.core.ci_report import build_javascript_report

        return build_javascript_report(
            config=config,
            tool_outputs=tool_outputs,
            tools_configured=tools_configured,
            tools_ran=tools_ran,
            tools_success=tools_success,
            thresholds=thresholds,
            context=context,
            tools_require_run=tools_require_run,
        )
```

---

## Registry Update

**File:** `cihub/core/languages/registry.py`

```python
# Add to _init_strategies():
def _init_strategies() -> dict[str, LanguageStrategy]:
    from cihub.core.languages.java import JavaStrategy
    from cihub.core.languages.javascript import JavaScriptStrategy  # ADD THIS
    from cihub.core.languages.python import PythonStrategy

    return {
        "python": PythonStrategy(),
        "java": JavaStrategy(),
        "javascript": JavaScriptStrategy(),  # ADD THIS
    }
```

---

## Tool Registry Update

**File:** `cihub/tools/registry.py`

```python
# Add new tools list:
JAVASCRIPT_TOOLS: list[str] = [
    "jest",
    "eslint",
    "prettier",
    "tsc",
    "npm_audit",
    "sbom",
    "semgrep",
    "trivy",
    "codeql",
]
```

---

## Schema Update

**File:** `schema/ci-hub-config.schema.json`

```json
{
  "properties": {
    "language": {
      "type": "string",
      "enum": ["python", "java", "javascript"]  // ADD "javascript"
    },
    "javascript": {
      "type": "object",
      "description": "JavaScript/TypeScript configuration",
      "properties": {
        "package_manager": {
          "type": "string",
          "enum": ["npm", "yarn", "pnpm"],
          "default": "npm"
        },
        "tools": {
          "type": "object",
          "properties": {
            "jest": { "$ref": "#/$defs/tool_config" },
            "eslint": { "$ref": "#/$defs/tool_config" },
            "prettier": { "$ref": "#/$defs/tool_config" },
            "tsc": { "$ref": "#/$defs/tool_config" },
            "npm_audit": { "$ref": "#/$defs/tool_config" },
            "semgrep": { "$ref": "#/$defs/tool_config" },
            "trivy": { "$ref": "#/$defs/tool_config" },
            "codeql": { "$ref": "#/$defs/tool_config" },
            "sbom": { "$ref": "#/$defs/tool_config" }
          }
        }
      }
    }
  }
}
```

---

## Defaults Update

**File:** `config/defaults.yaml`

```yaml
javascript:
  package_manager: npm
  node_version: "20"
  tools:
    jest:
      enabled: true
      min_coverage: 70
    eslint:
      enabled: true
      fail_on_error: true
    prettier:
      enabled: true
    tsc:
      enabled: true
    npm_audit:
      enabled: true
      fail_on_high: true
    semgrep:
      enabled: false
    trivy:
      enabled: false
    codeql:
      enabled: false
    sbom:
      enabled: false

thresholds:
  # Add JavaScript thresholds
  max_eslint_errors: 0
  max_npm_audit_vulns: 0
```

---

## Common JavaScript/Node.js Tools Reference

When implementing JavaScript support, consider these common tools:

### Testing
| Tool | Purpose | npm package |
|------|---------|-------------|
| jest | Test runner + coverage | `jest` |
| vitest | Fast Vite-native testing | `vitest` |
| mocha | Flexible test framework | `mocha` |
| c8 | Native V8 coverage | `c8` |

### Linting
| Tool | Purpose | npm package |
|------|---------|-------------|
| eslint | JavaScript linter | `eslint` |
| prettier | Code formatter | `prettier` |
| tsc | TypeScript compiler (type checking) | `typescript` |

### Security
| Tool | Purpose | npm package |
|------|---------|-------------|
| npm audit | Dependency vulnerabilities | built-in |
| snyk | Security scanning | `snyk` |
| retire | Known vulnerable packages | `retire` |

### Build
| Tool | Purpose | npm package |
|------|---------|-------------|
| webpack | Bundler | `webpack` |
| esbuild | Fast bundler | `esbuild` |
| vite | Next-gen build tool | `vite` |

---

## Validation Checklist

After adding a new language, verify:

- [ ] Strategy class implements all 8 required abstract methods
- [ ] Strategy registered in `registry.py`
- [ ] Tools listed in `tools/registry.py`
- [ ] Schema updated with language enum and tools section
- [ ] Defaults added to `config/defaults.yaml`
- [ ] `get_strategy("javascript")` returns the strategy
- [ ] `detect_language()` detects the language from project files
- [ ] All tool runners are callable
- [ ] Gates evaluate correctly with mock data
- [ ] Tests pass: `pytest tests/test_javascript_strategy.py`

---

## AI Integration Points

When AI is assisting with language addition:

1. **Research Phase**
   - Look up common CI tools for the language
   - Find typical threshold values
   - Identify project detection markers (package.json, go.mod, etc.)

2. **Generation Phase**
   - Generate strategy class following the template above
   - Generate tool runner stubs
   - Update registry, schema, and defaults

3. **Validation Phase**
   - Run schema validation
   - Run existing tests
   - Generate new tests for the strategy

4. **Human Review**
   - All generated code should be reviewed
   - Tool runners may need manual implementation
   - Thresholds may need adjustment

---

## Testing the New Language

```bash
# Run strategy tests
pytest tests/test_javascript_strategy.py -v

# Validate schema
python -c "import jsonschema; jsonschema.validate(...)"

# Test language detection
python -c "from cihub.core.languages import detect_language; print(detect_language(Path('/path/to/js-project')))"

# Integration test
cihub ci --language javascript --repo /path/to/test-repo --dry-run
```
