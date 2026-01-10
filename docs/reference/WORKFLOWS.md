# Workflows Reference

> **Generated Reference** - DO NOT EDIT MANUALLY  
> This document describes the GitHub Actions workflows in `.github/workflows/`.  

> For usage guidance, see [guides/WORKFLOWS.md](../guides/WORKFLOWS.md).  
> **Last Updated:** 2026-01-09  

---

## Workflow Overview

| Workflow | Purpose | Trigger | Target |
|----------|---------|---------|--------|
| `hub-production-ci.yml` | Hub repo CI/CD | push, PR, schedule, manual | Hub repo only |
| `hub-run-all.yml` | Central test runner | manual, schedule | All configured repos |
| `hub-orchestrator.yml` | Distributed dispatch | manual | Repos with workflows |
| `hub-security.yml` | Security-focused dispatch | manual | Repos with workflows |
| `java-ci.yml` | Java reusable workflow | workflow_call | Any Java repo |
| `python-ci.yml` | Python reusable workflow | workflow_call | Any Python repo |
| `hub-ci.yml` | Router to language workflows | workflow_call | Any repo |
| `smoke-test.yml` | Smoke test validation | manual | Fixture repos |
| `config-validate.yml` | Config schema validation | push, PR | Hub repo |
| `release.yml` | Release automation | push (tags) | Hub repo |
| `sync-templates.yml` | Template synchronization | manual | Template files |
| `template-guard.yml` | Template drift detection | PR | Templates |
| `kyverno-ci.yml` | Kyverno policy testing | workflow_call | Policy repos |
| `kyverno-validate.yml` | Kyverno validation | push, PR | Hub repo |

---

## Hub Production CI

**File:** `.github/workflows/hub-production-ci.yml`

Comprehensive CI for the hub repository itself.

### Triggers

| Trigger | Condition |
|---------|-----------|
| `push` | branches: `main`, `master`; paths: `cihub/`, `scripts/`, `tests/`, `templates/`, `config/`, `schema/`, `.github/workflows/`, `pyproject.toml`, `requirements*.txt` |
| `pull_request` | Same paths as push |
| `workflow_dispatch` | Manual with debug inputs |
| `schedule` | Weekly (Mondays 6 AM UTC) |

### Manual Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `cihub_debug` | boolean | false | Enable CIHUB_DEBUG |
| `cihub_verbose` | boolean | false | Enable CIHUB_VERBOSE |
| `cihub_debug_context` | boolean | false | Enable CIHUB_DEBUG_CONTEXT |

### Stages

1. **Stage 0:** Workflow Security (actionlint, zizmor)
2. **Stage 1:** Fast checks (lint, syntax, type)
3. **Stage 2:** Testing (unit, mutation)
4. **Stage 3:** Security (SAST, dependency audit, secrets, trivy)
5. **Stage 4:** Validation (templates, configs, schemas)
6. **Stage 5:** Supply Chain (scorecard, dependency-review)
7. **Stage 6:** Summary

---

## Hub Run All (Central Mode)

**File:** `.github/workflows/hub-run-all.yml`

Central test runner - clones and tests all configured repos.

### Triggers

| Trigger | Condition |
|---------|-----------|
| `workflow_dispatch` | Manual with filter/override inputs |
| `schedule` | Nightly (2 AM UTC) |

### Manual Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `repos` | string | (empty) | Specific repos (comma-separated, empty=all) |
| `run_group` | string | (empty) | Run group filter (full, smoke, fixtures) |
| `skip_mutation` | string | (empty) | Override: Skip mutation testing |
| `write_github_summary` | string | (empty) | Override: Write summary |
| `include_details` | string | (empty) | Override: Include per-repo details |
| `cihub_debug` | string | (empty) | Override: Enable CIHUB_DEBUG |
| `cihub_verbose` | string | (empty) | Override: Enable CIHUB_VERBOSE |
| `cihub_debug_context` | string | (empty) | Override: Enable CIHUB_DEBUG_CONTEXT |
| `cihub_emit_triage` | string | (empty) | Override: Enable CIHUB_EMIT_TRIAGE |
| `harden_runner_policy` | string | (empty) | Override: Harden-runner policy |

---

## Java CI (Reusable)

**File:** `.github/workflows/java-ci.yml`

Reusable workflow for Java projects.

### Trigger

| Trigger | Usage |
|---------|-------|
| `workflow_call` | Called via `uses: jguida941/ci-cd-hub/.github/workflows/java-ci.yml@v1` |

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `java_version` | string | `'21'` | Java version |
| `build_tool` | string | `'maven'` | Build tool (maven/gradle) |
| `run_jacoco` | boolean | true | Run JaCoCo coverage |
| `run_checkstyle` | boolean | true | Run Checkstyle |
| `run_spotbugs` | boolean | true | Run SpotBugs |
| `run_owasp` | boolean | true | Run OWASP Dependency Check |
| `use_nvd_api_key` | boolean | true | Use NVD API key |
| `run_pitest` | boolean | true | Run PITest mutation |
| `run_jqwik` | boolean | false | Run jqwik property testing |
| `run_codeql` | boolean | false | Run CodeQL (expensive) |
| `run_pmd` | boolean | true | Run PMD static analysis |
| `run_semgrep` | boolean | false | Run Semgrep SAST (expensive) |
| `run_trivy` | boolean | false | Run Trivy scanning |

### Caller Example

```yaml
# .github/workflows/hub-ci.yml
jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/java-ci.yml@v1
    secrets: inherit
```

---

## Python CI (Reusable)

**File:** `.github/workflows/python-ci.yml`

Reusable workflow for Python projects.

### Trigger

| Trigger | Usage |
|---------|-------|
| `workflow_call` | Called via `uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1` |

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `python_version` | string | `'3.12'` | Python version |
| `run_pytest` | boolean | true | Run pytest with coverage |
| `run_ruff` | boolean | true | Run Ruff linter |
| `run_bandit` | boolean | true | Run Bandit security |
| `run_pip_audit` | boolean | true | Run pip-audit |
| `run_mypy` | boolean | false | Run mypy type checker |
| `run_black` | boolean | true | Run Black format check |
| `run_isort` | boolean | true | Run isort import check |
| `run_mutmut` | boolean | true | Run mutmut mutation |
| `run_hypothesis` | boolean | true | Run Hypothesis property testing |
| `run_semgrep` | boolean | false | Run Semgrep SAST (expensive) |
| `run_sbom` | boolean | false | Generate SBOM (expensive) |
| `run_trivy` | boolean | false | Run Trivy scanning |

### Caller Example

```yaml
# .github/workflows/hub-ci.yml
jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
    secrets: inherit
```

---

## Hub Orchestrator (Distributed Mode)

**File:** `.github/workflows/hub-orchestrator.yml`

Dispatches CI to repos that have their own workflows.

### Triggers

| Trigger | Usage |
|---------|-------|
| `workflow_dispatch` | Manual with repo/group filters |

### Key Inputs

| Input | Type | Description |
|-------|------|-------------|
| `repos` | string | Specific repos (comma-separated) |
| `run_group` | string | Run group filter |

---

## Smoke Test

**File:** `.github/workflows/smoke-test.yml`

Validates hub functionality against fixture repos.

### Triggers

| Trigger | Usage |
|---------|-------|
| `workflow_dispatch` | Manual |

---

## Config Validate

**File:** `.github/workflows/config-validate.yml`

Validates hub configs against JSON schema.

### Triggers

| Trigger | Condition |
|---------|-----------|
| `push` | paths: `config/**`, `schema/**` |
| `pull_request` | paths: `config/**`, `schema/**` |

---

## Related Documentation

- [WORKFLOWS.md (Guide)](../guides/WORKFLOWS.md) - Usage guidance and setup
- [CONFIG.md](CONFIG.md) - Configuration reference
- [CLI.md](CLI.md) - CLI command reference
- [TOOLS.md](TOOLS.md) - Tool documentation
