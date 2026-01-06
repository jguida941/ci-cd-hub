# CI/CD Hub: Architectural Overview
> **Status:** Audited
> **Last Updated:** 2026-01-06
> **Author:** Justin Guida  
>
This document provides a comprehensive overview of the CI/CD Hub platform,
detailing its architecture, core components, execution modes, toolchains,
reporting mechanisms, and current status.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              CI/CD HUB (hub-release)                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │   CONFIG     │   │   SCHEMAS    │   │  WORKFLOWS   │   │     CLI      │ │
│  │   LAYER      │   │   LAYER      │   │    LAYER     │   │    TOOL      │ │
│  │              │   │              │   │              │   │   (cihub)    │ │
│  │ defaults.yaml│   │ ci-hub-*.json│   │ hub-run-all  │   │              │ │
│  │ repos/*.yaml │   │ ci-report.v2 │   │ java-ci.yml  │   │ 28 commands  │ │
│  │ templates/   │   │              │   │ python-ci.yml│   │ 2120 tests   │ │
│  │ profiles/    │   │              │   │              │   │              │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│          │                  │                  │                  │        │
│          └──────────────────┴──────────────────┴──────────────────┘        │
│                                      │                                     │
│                             ┌────────▼────────┐                            │
│                             │   AGGREGATION   │                            │
│                             │     ENGINE      │                            │
│                             │ (summary.json)  │                            │
│                             └─────────────────┘                            │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          ▼                            ▼                            ▼
   ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
   │  Java Repo  │              │ Python Repo │              │ Monorepo    │
   │ (11 tools)  │              │ (13 tools)  │              │ (multi-lang)│
   └─────────────┘              └─────────────┘              └─────────────┘
```

**Primary Hub Workflows:**
- `hub-run-all.yml` - central execution for all repos
- `hub-orchestrator.yml` - dispatch execution into repo callers
- `hub-security.yml` - scheduled security scans
- `hub-production-ci.yml` - CI for the hub repository itself

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
- Protected fields (`owner`, `name`, `language`, `dispatch_workflow`,
  `dispatch_enabled`) prevent accidental override
- JSON Schema v7 validation on all configs
- 12 pre-built profiles (java/python × minimal, fast, quality, coverage-gate,
  compliance, security) stored under `templates/profiles/`
- Hub CI config (`hub_ci`) governs `hub-production-ci.yml` using the same
  boolean toggle pattern as repo configs

---

### 2. Dual Execution Modes

| Mode            | Workflow               | How                 | Use Case        |
|-----------------|------------------------|---------------------|-----------------|
| **Central**     | `hub-run-all.yml`      | Run in hub          | No repo changes |
| **Distributed** | `hub-orchestrator.yml` | Dispatch repo calls | Repo autonomy   |

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

**Java (11 tools):**
```
┌────────────────────────────────────────────────────────────────┐
│ DEFAULT ON   │ OPT-IN           │ EXPENSIVE (OPT-IN)           │
├──────────────┼──────────────────┼──────────────────────────────┤
│ • JaCoCo     │ • jqwik          │ • Semgrep                    │
│ • Checkstyle │                  │ • Trivy                      │
│ • SpotBugs   │                  │ • CodeQL                     │
│ • PMD        │                  │ • Docker                     │
│ • OWASP DC   │                  │                              │
│ • PITest     │                  │                              │
└────────────────────────────────────────────────────────────────┘
```

**Python (13 tools):**
```
┌────────────────────────────────────────────────────────────────┐
│ DEFAULT ON   │ OPT-IN           │ EXPENSIVE (OPT-IN)           │
├──────────────┼──────────────────┼──────────────────────────────┤
│ • pytest     │ • mypy           │ • Semgrep                    │
│ • Ruff       │                  │ • Trivy                      │
│ • Black      │                  │ • CodeQL                     │
│ • isort      │                  │ • Docker                     │
│ • Bandit     │                  │                              │
│ • pip-audit  │                  │                              │
│ • mutmut     │                  │                              │
│ • Hypothesis │                  │                              │
└────────────────────────────────────────────────────────────────┘
```

**Java Tool Details:**

| Tool       | Purpose                | Config Key                   | Plugin                  |
|------------|------------------------|------------------------------|-------------------------|
| JaCoCo     | Code coverage          | `jacoco.min_coverage`        | `jacoco-maven-plugin`   |
| Checkstyle | Code style             | `checkstyle.fail_on_violation` | `maven-checkstyle-plugin` |
| SpotBugs   | Bug detection          | `spotbugs.effort`            | `spotbugs-maven-plugin` |
| PMD        | Static analysis        | `pmd.max_violations`         | `maven-pmd-plugin`      |
| OWASP DC   | Dependency vulns       | `owasp.fail_on_cvss`         | `dependency-check-maven` |
| PITest     | Mutation testing       | `pitest.min_mutation_score`  | `pitest-maven`          |
| jqwik      | Property-based testing | `jqwik.enabled`              | `net.jqwik:jqwik`       |

**Python Tool Details:**

| Tool      | Purpose          | Config                                            |
|-----------|------------------|---------------------------------------------------|
| pytest    | Tests + coverage | `python.tools.pytest.min_coverage: 70`            |
| Ruff      | Fast linting     | `python.tools.ruff.fail_on_error: true`           |
| Black     | Code formatting  | `python.tools.black.fail_on_format_issues: false` |
| isort     | Import sorting   | `python.tools.isort.fail_on_issues: false`        |
| Bandit    | Security linting | `python.tools.bandit.fail_on_high: true`          |
| pip-audit | Dependency vulns | `python.tools.pip_audit.fail_on_vuln: true`       |
| mypy      | Type checking    | `python.tools.mypy.enabled`                       |
| mutmut    | Mutation testing | `python.tools.mutmut.min_mutation_score: 70`      |

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

### 5. CLI Tool (`cihub`) - v1.0.0

> **28 commands total.** See `cihub --help` or `docs/reference/CLI.md` for complete list.

| Category           | Commands                                                    |
|--------------------|-------------------------------------------------------------|
| **Setup**          | `detect`, `new`, `init`, `update`, `scaffold`               |
| **Validation**     | `validate`, `preflight`, `doctor`, `check`, `verify`        |
| **Config**         | `config show/set/enable/disable`, `config-outputs`          |
| **Secrets**        | `setup-secrets`, `setup-nvd`                                |
| **Java**           | `fix-pom`, `fix-deps`, `pom`                                |
| **Templates**      | `sync-templates`, `templates`                               |
| **CI/Reports**     | `ci`, `run`, `report`, `triage`, `dispatch`                 |
| **Docs**           | `docs generate/check/links`, `adr new/list/check`           |
| **Hub-CI**         | `hub-ci` (47 subcommands for workflow automation)           |

---

### 6. Data Flow Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURATION FLOW                               │
│                                                                          │
│   defaults.yaml ──▶ repos/*.yaml ──▶ .ci-hub.yml ──▶ Schema Validation   │
│                        (merge)          (merge)          (validate)      │
│                                                              │           │
│                                                              ▼           │
│                                                     Effective Config     │
└──────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          EXECUTION FLOW                                  │
│                                                                          │
│   hub-run-all.yml ──▶ Matrix Jobs ──▶ java/python-ci.yml ──▶ Tool Runs   │
│   (or orchestrator)                    (reusable)                        │
└──────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         REPORTING FLOW                                   │
│                                                                          │
│   Tool Outputs ──▶ report.json ──▶ Aggregation ──▶ summary.json/dashboard│
│                    (per repo)                      (cross-repo)          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Stats

| Metric             | Count                            |
|--------------------|----------------------------------|
| CLI Commands       | 28 main + 47 hub-ci subcommands  |
| Unit Tests         | 2120                             |
| ADRs               | 44                               |
| Configured Repos   | 24                               |
| Pre-built Profiles | 12                               |
| User Guides        | 8                                |
| Workflow Files     | 13                               |

---

## Current Status

See `docs/development/status/STATUS.md` for the authoritative status log.

| Component                        | Status      |
|----------------------------------|-------------|
| Central Mode (`hub-run-all.yml`) | ✅ Working   |
| Reusable Workflows               | ✅ Working   |
| CLI Tool                         | v1.0.0      |
| Report Schema                    | v2.0        |
| Unit Tests                       | ✅ 2120 pass |
| Smoke Tests                      | ✅ Passing   |
| Orchestrator (Distributed)       | ❌ Needs fix |
| Hub Security Workflow            | ❌ Needs fix |

---

## Simple CI/CD-Hub Architecture Summary for Quick Reference

**Toolchains:**
- Java: JaCoCo, Checkstyle, SpotBugs, PMD, OWASP DC, PITest, jqwik, Semgrep, Trivy, CodeQL, Docker.
- Python: pytest, Ruff, Black, isort, Bandit, pip-audit, mypy, mutmut, Hypothesis, Semgrep, Trivy, CodeQL, Docker.

**Full Docs Index:**
- [Full Docs Index](../../README.md)
- [Architecture Plan (Archived)](../archive/ARCHITECTURE_PLAN.md)
- [Current Status](../status/STATUS.md)
- [Troubleshooting](../../guides/TROUBLESHOOTING.md)
- [Smoke Test Guide](../../guides/INTEGRATION_SMOKE_TEST.md)
