# Workflows Reference

**Generated from:** `.github/workflows/*.yml`  
**Regenerate with:** `cihub docs generate`  

---

## Quick Reference

| Workflow | Purpose | Trigger | When to Use |
| -------- | ------- | ------- | ----------- |
| `ai-ci-loop.yml` | Custom workflow | manual | See workflow comments. |
| `config-validate.yml` | Config schema validation | push, PR, manual | Runs automatically when you change configs. Validates YAM... |
| `hub-ci.yml` | Language router | reusable | Call this if you want automatic language detection - it r... |
| `hub-orchestrator.yml` | Distributed dispatch | manual, schedule, push | Use when repos have their own workflows and you want CI r... |
| `hub-production-ci.yml` | Hub repo CI/CD | push, PR, manual, schedule | Runs automatically on the hub repo. You don't call this d... |
| `hub-run-all.yml` | Central test runner | manual, schedule, push | Use this to test all repos from the hub without needing w... |
| `hub-security.yml` | Security-focused dispatch | manual, schedule | Use for security-only scans across repos without running ... |
| `java-ci.yml` | Java reusable workflow | reusable | Call from your Java repo's workflow for standardized CI (... |
| `kyverno-ci.yml` | Kyverno policy testing | reusable | Call from repos with Kyverno policies to validate them. |
| `kyverno-validate.yml` | Kyverno validation | push, PR, manual | Validates Kyverno policies in the hub repo. |
| `publish-pypi.yml` | Custom workflow | release, push | See workflow comments. |
| `python-ci.yml` | Python reusable workflow | reusable | Call from your Python repo's workflow for standardized CI... |
| `release.yml` | Release automation | push | Triggered by pushing version tags (v*). Creates GitHub re... |
| `smoke-test.yml` | Smoke test validation | manual, PR | Run manually to validate the hub works with fixture repos... |
| `sync-templates.yml` | Template sync | push, manual | Syncs template files to target repos. Run manually when t... |
| `template-guard.yml` | Template drift detection | PR, schedule, manual | Runs on PRs to detect if templates have drifted from source. |

---

## AI CI Loop

**File:** `.github/workflows/ai-ci-loop.yml`

Custom workflow.

**When to use:** See workflow comments.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_dispatch` | Manual trigger with inputs |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `max_iterations` | string | no | `5` | Maximum fix iterations |
| `fix_mode` | choice | no | `safe` | Fix strategy |

---

## Validate Hub Configs

**File:** `.github/workflows/config-validate.yml`

Config schema validation.

**When to use:** Runs automatically when you change configs. Validates YAML against schema.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `push` | branches: main, master; 4 path filters |
| `pull_request` | - |
| `workflow_dispatch` | Manual trigger with inputs |

---

## Hub CI

**File:** `.github/workflows/hub-ci.yml`

Language router.

**When to use:** Call this if you want automatic language detection - it routes to java-ci or python-ci.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_call` | Reusable workflow (called via `uses:`) |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `hub_correlation_id` | string | no | (empty) | Correlation ID from hub orchestrator for run matching |
| `hub_repo` | string | no | (empty) | Override hub repo (owner/name) for installing cihub |
| `hub_ref` | string | no | (empty) | Override hub ref (tag/sha/branch) for installing cihub |
| `cihub_debug` | boolean | no | false | Enable CIHUB_DEBUG |
| `cihub_verbose` | boolean | no | false | Enable CIHUB_VERBOSE |
| `cihub_debug_context` | boolean | no | false | Enable CIHUB_DEBUG_CONTEXT |
| `cihub_emit_triage` | boolean | no | false | Enable CIHUB_EMIT_TRIAGE |

---

## Hub Orchestrator

**File:** `.github/workflows/hub-orchestrator.yml`

Distributed dispatch.

**When to use:** Use when repos have their own workflows and you want CI results in each repo's Actions tab (Distributed Mode).

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_dispatch` | Manual trigger with inputs |
| `schedule` | cron: 0 2 * * * |
| `push` | branches: main, master; 2 path filters |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `repos` | string | no | (empty) | Comma-separated repo names (empty = all) |
| `write_github_summary` | string | no | (empty) | Override: Write summary to GITHUB_STEP_SUMMARY |
| `include_details` | string | no | (empty) | Override: Include per-repo details in summary |
| `cihub_debug` | string | no | (empty) | Override: Enable CIHUB_DEBUG |
| `cihub_verbose` | string | no | (empty) | Override: Enable CIHUB_VERBOSE |
| `cihub_debug_context` | string | no | (empty) | Override: Enable CIHUB_DEBUG_CONTEXT |
| `cihub_emit_triage` | string | no | (empty) | Override: Enable CIHUB_EMIT_TRIAGE |
| `harden_runner_policy` | string | no | (empty) | Override: Harden-runner policy (audit/block/disabled) |

---

## Hub Production CI

**File:** `.github/workflows/hub-production-ci.yml`

Hub repo CI/CD.

**When to use:** Runs automatically on the hub repo. You don't call this directly.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `push` | branches: main, master; 10 path filters |
| `pull_request` | - |
| `workflow_dispatch` | Manual trigger with inputs |
| `schedule` | cron: 0 6 * * 1 |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `cihub_debug` | boolean | no | false | Enable CIHUB_DEBUG |
| `cihub_verbose` | boolean | no | false | Enable CIHUB_VERBOSE |
| `cihub_debug_context` | boolean | no | false | Enable CIHUB_DEBUG_CONTEXT |

---

## Hub: Run All Repos

**File:** `.github/workflows/hub-run-all.yml`

Central test runner.

**When to use:** Use this to test all repos from the hub without needing workflows in each repo (Central Mode).

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_dispatch` | Manual trigger with inputs |
| `schedule` | cron: 0 2 * * * |
| `push` | branches: main, master; 1 path filters |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `repos` | string | no | (empty) | Specific repos (comma-separated, empty=all) |
| `run_group` | string | no | (empty) | Run group filter (full, smoke, fixtures, or comma-separated) |
| `skip_mutation` | string | no | (empty) | Override: Skip mutation testing |
| `write_github_summary` | string | no | (empty) | Override: Write summary to GITHUB_STEP_SUMMARY |
| `include_details` | string | no | (empty) | Override: Include per-repo details in summary |
| `cihub_debug` | string | no | (empty) | Override: Enable CIHUB_DEBUG |
| `cihub_verbose` | string | no | (empty) | Override: Enable CIHUB_VERBOSE |
| `cihub_debug_context` | string | no | (empty) | Override: Enable CIHUB_DEBUG_CONTEXT |
| `cihub_emit_triage` | string | no | (empty) | Override: Enable CIHUB_EMIT_TRIAGE |
| `harden_runner_policy` | string | no | (empty) | Override: Harden-runner policy (audit/block/disabled) |

---

## Hub: Security & Supply Chain

**File:** `.github/workflows/hub-security.yml`

Security-focused dispatch.

**When to use:** Use for security-only scans across repos without running full CI.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_dispatch` | Manual trigger with inputs |
| `schedule` | cron: 0 3 * * 0 |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `repos` | string | no | (empty) | Specific repos (comma-separated, empty=all) |
| `run_zap` | boolean | no | false | Run ZAP DAST scan (requires running app) |
| `write_github_summary` | boolean | no | true | Write summary to GITHUB_STEP_SUMMARY |
| `harden_runner_policy` | string | no | `audit` | Harden-runner policy: audit (default), block, or disabled |

---

## Java CI Pipeline

**File:** `.github/workflows/java-ci.yml`

Java reusable workflow.

**When to use:** Call from your Java repo's workflow for standardized CI (tests, coverage, linting, security).

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_call` | Reusable workflow (called via `uses:`) |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `java_version` | string | no | `21` | Java version |
| `build_tool` | string | no | `maven` | Build tool (maven or gradle) |
| `run_jacoco` | boolean | no | true | Run JaCoCo coverage |
| `run_checkstyle` | boolean | no | true | Run Checkstyle |
| `run_spotbugs` | boolean | no | true | Run SpotBugs |
| `run_owasp` | boolean | no | true | Run OWASP Dependency Check |
| `use_nvd_api_key` | boolean | no | true | Use NVD API key for faster OWASP scans (requires NVD_API_KEY secret) |
| `run_pitest` | boolean | no | true | Run PITest mutation testing |
| `run_jqwik` | boolean | no | false | Run jqwik property-based testing |
| `run_codeql` | boolean | no | false | Run CodeQL analysis (expensive) |
| `run_pmd` | boolean | no | true | Run PMD static analysis |
| `run_semgrep` | boolean | no | false | Run Semgrep SAST (expensive) |
| `run_trivy` | boolean | no | false | Run Trivy container scan (expensive) |
| `run_sbom` | boolean | no | false | Generate SBOM (expensive) |
| `run_docker` | boolean | no | false | Build and test Docker |
| `run_harden_runner` | boolean | no | true | Enable StepSecurity harden-runner for workflow security |
| `harden_runner_egress_policy` | string | no | `audit` | Harden-runner egress policy: audit (log only) or block (deny unauthorized) |
| `coverage_min` | number | no | `70` | Minimum coverage percentage |
| `mutation_score_min` | number | no | `70` | Minimum mutation score |
| `owasp_cvss_fail` | number | no | `7` | CVSS score to fail on for OWASP (default: 7) |
| `trivy_cvss_fail` | number | no | `7` | CVSS score to fail on for Trivy (default: 7) |
| `max_critical_vulns` | number | no | `0` | Maximum allowed critical vulnerabilities across scanners |
| `max_high_vulns` | number | no | `0` | Maximum allowed high vulnerabilities across scanners |
| `max_semgrep_findings` | number | no | `0` | Maximum allowed Semgrep findings (default: 0 = fail on any) |
| `max_pmd_violations` | number | no | `0` | Maximum allowed PMD violations (default: 0 = fail on any) |
| `max_checkstyle_errors` | number | no | `0` | Maximum allowed Checkstyle errors (default: 0 = fail on any) |
| `max_spotbugs_bugs` | number | no | `0` | Maximum allowed SpotBugs bugs (default: 0 = fail on any) |
| `docker_compose_file` | string | no | `docker-compose.yml` | Docker compose file path |
| `docker_health_endpoint` | string | no | `/actuator/health` | Health check endpoint |
| `retention_days` | number | no | `30` | Artifact retention days |
| `workdir` | string | no | `.` | Working directory (monorepo subfolder, default repo root) |
| `artifact_prefix` | string | no | (empty) | Prefix for artifact names (use when calling multiple times in same workflow) |
| `hub_correlation_id` | string | no | (empty) | Correlation ID from hub orchestrator for run matching |
| `hub_repo` | string | no | (empty) | Override hub repo (owner/name) for installing cihub |
| `hub_ref` | string | no | (empty) | Override hub ref (tag/sha/branch) for installing cihub |
| `write_github_summary` | boolean | no | true | Write summary to GITHUB_STEP_SUMMARY |
| `cihub_debug` | boolean | no | false | Enable CIHUB_DEBUG |
| `cihub_verbose` | boolean | no | false | Enable CIHUB_VERBOSE |
| `cihub_debug_context` | boolean | no | false | Enable CIHUB_DEBUG_CONTEXT |
| `cihub_emit_triage` | boolean | no | false | Enable CIHUB_EMIT_TRIAGE |

---

## Kyverno CI

**File:** `.github/workflows/kyverno-ci.yml`

Kyverno policy testing.

**When to use:** Call from repos with Kyverno policies to validate them.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_call` | Reusable workflow (called via `uses:`) |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `policies_dir` | string | no | `policies/kyverno` | Directory containing Kyverno policy YAML files |
| `templates_dir` | string | no | `templates/kyverno` | Directory containing Kyverno policy templates |
| `fixtures_dir` | string | no | `fixtures/kyverno` | Directory containing test fixture resources |
| `run_tests` | boolean | no | false | Run policy tests against fixtures |
| `write_github_summary` | boolean | no | true | Write summary to GITHUB_STEP_SUMMARY |
| `hub_repo` | string | no | (empty) | Override hub repo (owner/name) for installing cihub |
| `hub_ref` | string | no | (empty) | Override hub ref (tag/sha/branch) for installing cihub |
| `kyverno_version` | string | no | `v1.16.1` | Kyverno CLI version |
| `fail_on_warn` | boolean | no | false | Fail if policies produce warnings |
| `workdir` | string | no | `.` | Working directory (for monorepos) |

---

## Kyverno: Validate Policies

**File:** `.github/workflows/kyverno-validate.yml`

Kyverno validation.

**When to use:** Validates Kyverno policies in the hub repo.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `push` | 4 path filters |
| `pull_request` | - |
| `workflow_dispatch` | Manual trigger with inputs |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `write_github_summary` | boolean | no | true | Write summary to GITHUB_STEP_SUMMARY |

---

## Publish to PyPI

**File:** `.github/workflows/publish-pypi.yml`

Custom workflow.

**When to use:** See workflow comments.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `release` | - |
| `push` | - |

---

## Python CI Pipeline

**File:** `.github/workflows/python-ci.yml`

Python reusable workflow.

**When to use:** Call from your Python repo's workflow for standardized CI (tests, coverage, linting, security).

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_call` | Reusable workflow (called via `uses:`) |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `python_version` | string | no | `3.12` | Python version |
| `run_pytest` | boolean | no | true | Run pytest with coverage |
| `run_ruff` | boolean | no | true | Run Ruff linter |
| `run_bandit` | boolean | no | true | Run Bandit security scanner |
| `run_pip_audit` | boolean | no | true | Run pip-audit dependency check |
| `run_mypy` | boolean | no | false | Run mypy type checker |
| `run_black` | boolean | no | true | Run Black format checker |
| `run_isort` | boolean | no | true | Run isort import checker |
| `run_mutmut` | boolean | no | true | Run mutmut mutation testing |
| `run_hypothesis` | boolean | no | true | Run Hypothesis property-based testing |
| `run_semgrep` | boolean | no | false | Run Semgrep SAST (expensive) |
| `run_sbom` | boolean | no | false | Generate SBOM (expensive) |
| `run_trivy` | boolean | no | false | Run Trivy container scan (expensive) |
| `run_docker` | boolean | no | false | Build and test Docker |
| `run_codeql` | boolean | no | false | Run CodeQL analysis (expensive) |
| `workdir` | string | no | `.` | Working directory (monorepo subfolder, default repo root) |
| `run_harden_runner` | boolean | no | true | Enable StepSecurity harden-runner for workflow security |
| `harden_runner_egress_policy` | string | no | `audit` | Harden-runner egress policy: audit (log only) or block (deny unauthorized) |
| `coverage_min` | number | no | `70` | Minimum coverage percentage |
| `mutation_score_min` | number | no | `70` | Minimum mutation score |
| `max_critical_vulns` | number | no | `0` | Maximum allowed critical vulnerabilities across scanners |
| `max_high_vulns` | number | no | `0` | Maximum allowed high vulnerabilities across scanners |
| `trivy_cvss_fail` | number | no | `7` | CVSS score to fail on for Trivy (default: 7) |
| `owasp_cvss_fail` | number | no | `7` | Legacy alias for trivy_cvss_fail (default: 7) |
| `max_semgrep_findings` | number | no | `0` | Maximum allowed Semgrep findings (default: 0 = fail on any) |
| `max_black_issues` | number | no | `0` | Maximum allowed Black formatting issues (default: 0 = fail on any) |
| `max_isort_issues` | number | no | `0` | Maximum allowed isort import issues (default: 0 = fail on any) |
| `max_ruff_errors` | number | no | `0` | Maximum allowed Ruff errors (default: 0 = fail on any) |
| `max_pip_audit_vulns` | number | no | `0` | Maximum allowed pip-audit vulnerabilities (default: 0 = fail on any) |
| `retention_days` | number | no | `30` | Artifact retention days |
| `artifact_prefix` | string | no | (empty) | Prefix for artifact names (use when calling multiple times in same workflow) |
| `hub_correlation_id` | string | no | (empty) | Correlation ID from hub orchestrator for run matching |
| `hub_repo` | string | no | (empty) | Override hub repo (owner/name) for installing cihub |
| `hub_ref` | string | no | (empty) | Override hub ref (tag/sha/branch) for installing cihub |
| `write_github_summary` | boolean | no | true | Write summary to GITHUB_STEP_SUMMARY |
| `cihub_debug` | boolean | no | false | Enable CIHUB_DEBUG |
| `cihub_verbose` | boolean | no | false | Enable CIHUB_VERBOSE |
| `cihub_debug_context` | boolean | no | false | Enable CIHUB_DEBUG_CONTEXT |
| `cihub_emit_triage` | boolean | no | false | Enable CIHUB_EMIT_TRIAGE |

---

## Release

**File:** `.github/workflows/release.yml`

Release automation.

**When to use:** Triggered by pushing version tags (v*). Creates GitHub releases.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `push` | - |

---

## Smoke Test

**File:** `.github/workflows/smoke-test.yml`

Smoke test validation.

**When to use:** Run manually to validate the hub works with fixture repos before releases.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `workflow_dispatch` | Manual trigger with inputs |
| `pull_request` | - |

### Inputs

| Input | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |
| `skip_mutation` | boolean | no | true | Skip mutation testing (faster - recommended) |
| `write_github_summary` | boolean | no | true | Write summary to GITHUB_STEP_SUMMARY |
| `harden_runner_policy` | string | no | `audit` | Harden-runner policy: audit (default), block, or disabled |

---

## Sync Templates

**File:** `.github/workflows/sync-templates.yml`

Template sync.

**When to use:** Syncs template files to target repos. Run manually when templates change.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `push` | 1 path filters |
| `workflow_dispatch` | Manual trigger with inputs |

---

## Template Guard

**File:** `.github/workflows/template-guard.yml`

Template drift detection.

**When to use:** Runs on PRs to detect if templates have drifted from source.

### Triggers

| Trigger | Details |
| ------- | ------- |
| `pull_request` | - |
| `schedule` | cron: 0 4 * * * |
| `workflow_dispatch` | Manual trigger with inputs |

---

## Related Documentation

- [WORKFLOWS.md (Guide)](../guides/WORKFLOWS.md) - Usage guidance and setup
- [CONFIG.md](CONFIG.md) - Configuration reference
- [CLI.md](CLI.md) - CLI command reference
- [TOOLS.md](TOOLS.md) - Tool documentation
