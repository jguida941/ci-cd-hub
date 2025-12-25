# CI/CD Hub - Architectural Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CI/CD HUB (hub-release)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │   CONFIG     │   │   SCHEMAS    │   │  WORKFLOWS   │   │     CLI      │ │
│  │   LAYER      │   │   LAYER      │   │    LAYER     │   │    TOOL      │ │
│  │              │   │              │   │              │   │   (cihub)    │ │
│  │ defaults.yaml│   │ ci-hub-*.json│   │ hub-run-all  │   │              │ │
│  │ repos/*.yaml │   │ ci-report.v2 │   │ java-ci.yml  │   │ 9 commands   │ │
│  │ profiles/    │   │              │   │ python-ci.yml│   │ 65 functions │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│          │                  │                  │                  │        │
│          └──────────────────┴──────────────────┴──────────────────┘        │
│                                      │                                      │
│                             ┌────────▼────────┐                            │
│                             │   AGGREGATION   │                            │
│                             │     ENGINE      │                            │
│                             │ (summary.json)  │                            │
│                             └─────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          ▼                            ▼                            ▼
   ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
   │  Java Repo  │              │ Python Repo │              │ Monorepo    │
   │ (10 tools)  │              │ (11 tools)  │              │ (multi-lang)│
   └─────────────┘              └─────────────┘              └─────────────┘
```

---

## Core Components

### 1. Configuration Management (3-Tier Hierarchy)

```
Priority (Highest → Lowest):
┌─────────────────────────────────────┐
│ .ci-hub.yml (in target repo)        │  ← Developer overrides
├─────────────────────────────────────┤
│ config/repos/<repo>.yaml            │  ← Hub admin settings
├─────────────────────────────────────┤
│ config/defaults.yaml                │  ← Global baseline
└─────────────────────────────────────┘
```

**Key Features:**
- Deep merge algorithm for nested overrides
- Protected fields (`owner`, `name`, `language`) prevent accidental override
- JSON Schema v7 validation on all configs
- 13 pre-built profiles (java-minimal → java-security, python-minimal → python-security)

---

### 2. Dual Execution Modes

| Mode | Workflow | How It Works | Use Case |
|------|----------|--------------|----------|
| **Central** | `hub-run-all.yml` | Hub clones repos & runs tests | Quick setup, no repo changes needed |
| **Distributed** | `hub-orchestrator.yml` | Dispatches to repo's own workflows | Repo autonomy, faster feedback |

```
CENTRAL MODE                          DISTRIBUTED MODE
┌─────────────┐                       ┌─────────────┐
│  Hub Repo   │                       │  Hub Repo   │
│ (run-all)   │                       │(orchestrator)│
└──────┬──────┘                       └──────┬──────┘
       │ clone & test                        │ dispatch
       ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│  Matrix Job │                       │ Target Repo │
│ (per repo)  │                       │ (hub-ci.yml)│
└─────────────┘                       └──────┬──────┘
                                             │ calls
                                             ▼
                                      ┌─────────────┐
                                      │  Reusable   │
                                      │ java/python │
                                      │    -ci.yml  │
                                      └─────────────┘
```

---

### 3. Language-Specific Toolchains

**Java (10 tools):**
```
┌────────────────────────────────────────────────────────────────┐
│ ALWAYS       │ OPT-IN           │ EXPENSIVE                    │
├──────────────┼──────────────────┼──────────────────────────────┤
│ • JaCoCo     │ • PITest         │ • Semgrep                    │
│ • Checkstyle │ • OWASP DC       │ • Trivy                      │
│ • SpotBugs   │ • jqwik          │ • CodeQL                     │
│ • PMD        │                  │                              │
└────────────────────────────────────────────────────────────────┘
```

**Python (11 tools):**
```
┌────────────────────────────────────────────────────────────────┐
│ ALWAYS       │ OPT-IN           │ EXPENSIVE                    │
├──────────────┼──────────────────┼──────────────────────────────┤
│ • pytest     │ • mypy           │ • Semgrep                    │
│ • Ruff       │ • mutmut         │ • Trivy                      │
│ • Black      │ • Hypothesis     │ • CodeQL                     │
│ • isort      │                  │                              │
│ • Bandit     │                  │                              │
│ • pip-audit  │                  │                              │
└────────────────────────────────────────────────────────────────┘
```

**Java Tool Details:**
| Tool | Purpose | Config | Maven Plugin |
|------|---------|--------|--------------|
| JaCoCo | Code coverage | `java.tools.jacoco.min_coverage: 70` | `org.jacoco:jacoco-maven-plugin` |
| Checkstyle | Code style | `java.tools.checkstyle.fail_on_violation: true` | `maven-checkstyle-plugin` |
| SpotBugs | Bug detection | `java.tools.spotbugs.effort: max` | `spotbugs-maven-plugin` |
| PMD | Static analysis | `java.tools.pmd.max_violations: 0` | `maven-pmd-plugin` |
| OWASP DC | Dependency vulns | `java.tools.owasp.fail_on_cvss: 7` | `dependency-check-maven` |
| PITest | Mutation testing | `java.tools.pitest.min_mutation_score: 70` | `pitest-maven` |
| jqwik | Property-based testing | `java.tools.jqwik.enabled: true` | Dependency: `net.jqwik:jqwik` |

**Python Tool Details:**
| Tool | Purpose | Config |
|------|---------|--------|
| pytest | Tests + coverage | `python.tools.pytest.min_coverage: 70` |
| Ruff | Fast linting | `python.tools.ruff.fail_on_error: true` |
| Black | Code formatting | `python.tools.black.fail_on_format_issues: false` |
| isort | Import sorting | `python.tools.isort.fail_on_issues: false` |
| Bandit | Security linting | `python.tools.bandit.fail_on_high: true` |
| pip-audit | Dependency vulns | `python.tools.pip_audit.fail_on_vuln: true` |
| mypy | Type checking | `python.tools.mypy.enabled: true` |
| mutmut | Mutation testing | `python.tools.mutmut.min_mutation_score: 70` |

All tools are simple booleans: `enabled: true/false` with optional thresholds.

---

### 4. Report & Aggregation Pipeline

```
Per-Repository Run                      Hub Aggregation
┌─────────────────┐                    ┌─────────────────┐
│   Tool Outputs  │                    │  All report.json│
│  (XML, JSON)    │                    │     files       │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│  report.json    │───────────────────▶│   Validate      │
│  (schema v2.0)  │                    │   Against       │
│                 │                    │   Schema        │
│ • coverage      │                    └────────┬────────┘
│ • mutation_score│                             │
│ • tests_passed  │                             ▼
│ • tool_metrics  │                    ┌─────────────────┐
│ • tools_ran     │                    │  summary.json   │
│ • tools_success │                    │                 │
└─────────────────┘                    │ • avg coverage  │
                                       │ • avg mutation  │
                                       │ • total vulns   │
                                       │ • pass/fail     │
                                       └─────────────────┘
```

---

### 5. CLI Tool (`cihub`) - v0.2.0

| Command | Purpose |
|---------|---------|
| `detect` | Auto-detect Java/Python from project files |
| `init` | Generate `.ci-hub.yml` + caller workflow |
| `update` | Refresh existing config |
| `validate` | Validate config + check POM plugins |
| `setup-secrets` | Configure `HUB_DISPATCH_TOKEN` |
| `setup-nvd` | Configure `NVD_API_KEY` for OWASP |
| `fix-pom` | Auto-add missing Maven plugins |
| `fix-deps` | Auto-add missing Maven dependencies |
| `sync-templates` | Push caller workflows to target repos |

---

### 6. Data Flow Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURATION FLOW                                │
│                                                                          │
│   defaults.yaml ──▶ repos/*.yaml ──▶ .ci-hub.yml ──▶ Schema Validation   │
│                        (merge)          (merge)          (validate)       │
│                                                              │            │
│                                                              ▼            │
│                                                     Effective Config      │
└──────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          EXECUTION FLOW                                   │
│                                                                          │
│   hub-run-all.yml ──▶ Matrix Jobs ──▶ java/python-ci.yml ──▶ Tool Runs   │
│   (or orchestrator)                    (reusable)                         │
└──────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         REPORTING FLOW                                    │
│                                                                          │
│   Tool Outputs ──▶ report.json ──▶ Aggregation ──▶ summary.json/Dashboard│
│                    (per repo)                      (cross-repo)          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Stats

| Metric | Count |
|--------|-------|
| Workflow YAML | ~7,900 lines |
| CLI Tool | 1,688 lines, 65 functions |
| Configured Repos | 13 |
| Pre-built Profiles | 13 |
| ADRs | 25 |
| Unit Tests | 80+ |
| User Guides | 8 |

---

## Current Status

| Component | Status |
|-----------|--------|
| Central Mode (`hub-run-all.yml`) | ✅ Passing |
| Reusable Workflows | ✅ Working |
| CLI Tool | ✅ v0.2.0 |
| Schema Validation | ✅ v2.0 |
| Smoke Tests | ✅ Passing |
| Orchestrator (Distributed) | ❌ Needs fix |
| Hub Security Workflow | ❌ Needs fix |

---

## For Presentations

**One-liner:** *"A self-validating CI/CD platform that centralizes configuration, generates deterministic workflows, validates outputs against schemas, and aggregates results across Java and Python repositories."*

**Key differentiators:**
1. **Schema-driven** - All configs validated before execution
2. **Dual-mode** - Central (quick) or Distributed (autonomous)
3. **Language-aware** - 10 Java tools, 11 Python tools, auto-detection
4. **Self-healing** - CLI auto-fixes Maven POMs, syncs templates
5. **Observable** - Aggregated reports with unified format
6. **Extensible** - Profile system for rapid onboarding
