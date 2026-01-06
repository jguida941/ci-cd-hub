# Changelog

All notable changes to this project will be documented in this file.

## 2026-01-06 - Security Audit + Consistency Fixes

### Security Fixes (CRITICAL)

**ZIP Path Traversal (CVE-2007-4559 variant):**
- Added `_safe_extractall()` helper with `Path.relative_to()` validation
- Fixed in: `cihub/core/correlation.py`, `cihub/core/aggregation/github_api.py`, `scripts/debug_orchestrator.py`
- Pattern: Validate each ZIP member path stays within target directory before extraction

**Tarball Symlink Attack:**
- Added `issym()` and `islnk()` rejection before tarball extraction
- Fixed in: `cihub/commands/hub_ci/__init__.py`
- Pattern: Reject symbolic links and hard links in tarballs

### Consistency Fixes (23 Low Severity Issues)

**Token Environment Variable Priority:**
- Added `get_github_token()` helper to `cihub/utils/env.py`
- Standardized priority: `GH_TOKEN` → `GITHUB_TOKEN` → `HUB_DISPATCH_TOKEN`
- Updated: `templates.py`, `dispatch.py`, `aggregate.py`

**Safe Integer Parsing:**
- Added `env_int()` helper to `cihub/utils/env.py`
- Updated: `release.py` (Trivy env var parsing)

**Exit Code Consistency:**
- `smoke.py` now returns `EXIT_FAILURE` when tests fail (was always SUCCESS)
- Added problem entry with error code `CIHUB-SMOKE-TEST-FAILURE`

**Path Traversal Prevention:**
- Added `validate_subdir()` calls to `init.py`, `new.py`

**Magic Number Constants:**
- Added `MAX_LOG_PREVIEW_CHARS = 2000` to `python_tools.py`
- Added `MAX_ERRORS_IN_TRIAGE = 20` to `triage.py`
- Added `HEALTH_CHECK_INTERVAL_SECONDS = 5` and `HEALTH_CHECK_HTTP_TIMEOUT_SECONDS = 5` to `docker_tools.py`

**Code Consolidation:**
- `get_tool_enabled()` in `config/loader/core.py` now delegates to canonical `tool_enabled()` from `normalize.py`

**API Cleanup:**
- Removed private functions from `__all__` in `utils/__init__.py`: `_parse_env_bool`, `_bar`, `_get_repo_name`, `_detect_java_project_type`
- Updated imports in `gates.py`, `java.py`, `build.py` to use public function names

### Test Updates
- Updated test assertions to match new behavior (2 tests)
- All 2120 tests passing

---

## 2026-01-05 - CommandResult Migration + Test Reorganization Plan

### Code Review Fixes (CLEAN_CODE.md Phase 3)

**Migration Quality Improvements:**
- **detect.py** — Pure CommandResult return (no conditional JSON mode)
- **validate.py** — Added YAML parse error handling (yaml.YAMLError, ValueError)
- **smoke.py** — Fixed TemporaryDirectory resource leak with explicit cleanup
- **discover.py** — Reordered empty check before GITHUB_OUTPUT write
- **cli.py** — Error output now routes to stderr (CLI best practice)

**Test Updates:**
- Updated test patterns: `result.exit_code` instead of comparing `result == int`
- Added `--json` flag to E2E detect tests for proper JSON output
- All 2101+ tests passing

### TEST_REORGANIZATION.md Plan Created

**New Design Doc:** `docs/development/active/TEST_REORGANIZATION.md`

Comprehensive plan for restructuring 2100+ tests from flat `tests/` into organized hierarchy:
- `tests/unit/` — Fast, isolated, no I/O
- `tests/integration/` — Cross-module, may use filesystem
- `tests/e2e/` — Full workflows, slow
- `tests/contracts/` — Schema/API contract tests
- `tests/property/` — Hypothesis property-based tests
- `tests/regression/` — Bug reproduction tests

**Living Metadata System:**
- Uses existing `config/defaults.yaml` `hub_ci.thresholds` as single source of truth
- Auto-generated test file headers with metrics
- Auto-generated `tests/README.md` with coverage table

### 5-Agent Parallel Audit

Completed comprehensive audit of TEST_REORGANIZATION.md plan identifying critical gaps:

| Aspect | Finding |
|--------|---------|
| Test Structure | 45% of files (35/78) don't fit proposed categories |
| Config Integration | `cihub hub-ci thresholds` CLI command not implemented |
| Schema | Per-module overrides blocked by `additionalProperties: false` |
| Automation | 3 scripts must be written (update_test_metrics, generate_test_readme, check_test_drift) |
| Drift Detection | Only ~20% of scenarios covered |

**Estimated effort:** ~10-12 days before Phase 1 can start

### Documentation Updates
- Updated STATUS.md with current progress and active design docs
- Updated MASTER_PLAN.md with code review fixes and TEST_REORGANIZATION references
- Added TEST_REORGANIZATION.md to Active Design Docs table

---

## 2026-01-05 - v1.0 Cutline + Plan Alignment

### MASTER_PLAN.md Updates
- Added **v1.0 Cutline** section with Quick Wins, Heavy Lifts, and Verification items.
- Created **Post v1.0 Backlog** section for explicitly deferred items:
  - Registry & Versioning (centralized registry CLI, versioning/rollback)
  - Triage Enhancements (schema validation, DORA metrics)
  - Governance (RBAC, approval workflows)
  - Optional Tooling (act integration, Gradle, Docker multi-stage)
  - PyQt6 GUI wrapper (deferred until CLI stabilizes)
- v1.0 Quick Wins: docs stale, docs audit, config validate, audit umbrella, --json everywhere, _tool_enabled consolidation, gate-spec refactor, CI-engine tests.
- v1.0 Heavy Lifts: env/context wrapper, runner/adapter boundaries.

### AGENTS.md Updates
- Updated "Current Focus" to link to MASTER_PLAN.md v1.0 cutline (single source of truth).
- Listed v1.0 Quick Wins in order for immediate reference.
- Removed duplicate/stale "Current Focus" items now covered by MASTER_PLAN.md.
- Extracted CI Parity Map (~50 lines) to `docs/development/CI_PARITY.md`; replaced with summary + link.
- Fixed aspirational claims: CLI output contract now notes hub-ci gaps, workflow install rule consolidated.
- Corrected parity map: verify-matrix-keys uses CLI (not script), license-check is partial match (CI adds --github-summary).

### New Documentation
- **`docs/development/CI_PARITY.md`**: Full CI parity map with Exact/Partial/CI-only/Local-only categories, check tier mapping, and maintenance notes.

### Governance
- Verified design doc references aligned between MASTER_PLAN.md and STATUS.md.
- All active design docs (CLEAN_CODE.md, DOC_AUTOMATION_AUDIT.md, PYQT_PLAN.md) properly referenced.
- Updated STATUS.md directory structure to include CI_PARITY.md.

## 2026-01-04 - Maintainability Audit (MASTER_PLAN.md §10)

### Audit Findings
- Multi-agent audit of CLI (87 commands), services, workflows, and automation plans.
- Identified 5 implementations of `_tool_enabled()` (54 usages) — consolidation needed.
- `test_services_ci.py` has only 2 tests — major coverage gap.
- `hub-ci` subcommands (47 commands) explicitly block `--json` flag.
- 21 unpinned `step-security/harden-runner` uses in workflows.
- 38+ `if language ==` branches — Language Strategies pattern needed.

### MASTER_PLAN.md Updates
- Added Section 10 (Maintainability Improvements) with CLI-compatible action items.
- All items follow ADR-0031 (CLI-first) — no composite actions or workflow logic.
- Linked to `active/CLEAN_CODE.md` for Language Strategies design.
- Added 4 new items from second audit pass:
  - Env/context wrapper (`GitHubContext` centralizes 17 `GITHUB_*` reads)
  - Runner/adapter boundaries (subprocess only in `ci_runner/`)
  - Output normalization (forbid `print()` in commands)
  - Performance guardrails + "no inline logic" workflow guard

### Dropped Recommendations
- Composite actions (violates CLI-first architecture).
- Workflow consolidation via modes (adds YAML complexity).
- Typer/pdoc migrations (nice-to-have, not needed).

## 2026-01-04 - Governance Alignment + Doc Automation Backlog

### Documentation Governance
- Expanded MASTER_PLAN.md References section to include all active design docs (CLEAN_CODE.md, DOC_AUTOMATION_AUDIT.md, PYQT_PLAN.md).
- Added Scope Guardrails #5 and #6 for active docs lifecycle (`active/` → `archive/` with superseded header).
- Added Section 6b (Documentation Automation) with full backlog from DOC_AUTOMATION_AUDIT.md design doc.
- Connected Section 9 (Triage/Registry/LLM) to doc freshness tooling via `.cihub/tool-outputs/`.
- Fixed AGENTS.md stale references: `PLAN.md` → `MASTER_PLAN.md` (3 occurrences).

### Documentation Automation Backlog (MASTER_PLAN.md §6b)
- `cihub docs stale`: AST symbol extraction, schema key diffing, CLI surface drift, file move/delete detection.
- `cihub docs audit`: active ↔ STATUS.md sync, archive header validation, plain-text reference scan, ADR metadata lint.
- `.cihub/tool-outputs/` artifacts: `docs_stale.json`, `docs_stale.prompt.md`, `docs_audit.json`.
- Doc manifest (`docs_manifest.json`) for LLM context.
- Generated references expansion: TOOLS.md from registry, WORKFLOWS.md from workflows.

## 2026-01-04 - Doc Lifecycle + ADR Updates

### Documentation
- Created `docs/development/active/` folder for in-flight design docs.
- Moved CLEAN_CODE.md, DOC_AUTOMATION_AUDIT.md, PYQT_PLAN.md to `active/`.
- Updated docs/README.md, MASTER_PLAN.md, STATUS.md with new folder structure.
- Added `cihub docs audit` spec to MASTER_PLAN.md (active ↔ STATUS.md consistency checks).
- Archived `docs/MAKE.md` → `development/archive/MAKE.md`.
- Consolidated Make guidance into GETTING_STARTED.md (pre-push workflow) and DEVELOPMENT.md (config/debug targets).
- Added "Make targets are CLI wrappers" note to both docs.
- Added Make target drift check to `cihub docs audit` spec (verify referenced targets exist in Makefile).

### ADRs
- ADR-0035: Changed Status from Proposed → Accepted; added Implementation Note.
- ADR-0031: Added Enforcement Addendum (what's allowed inline vs must use CLI).
- ADR-0018: Fixed broken link to SMOKE_TEST.md → INTEGRATION_SMOKE_TEST.md.

## 2026-01-05 - Config Loader Canonicalization + CLI Layering

### CLI
- Moved CLI helper imports in commands to services/utils (no CLI surface changes).
- Added a parser builder helper to support docs generation without importing `cihub.cli`.

### Config
- `load_ci_config`/`load_hub_config` now delegate to the canonical validated loader.
- Default config loading falls back to built-in defaults when `defaults.yaml` is empty or missing.
- Preserve repo-local `repo.owner`/`repo.name`/`repo.language` when no hub override exists.
- `load_effective_config` now delegates to the validated loader (schema-enforced).

### Tests
- Added Stage 2 AST boundary enforcement for core/services/commands layering.
- Updated .ci-hub.yml fixtures to include required repo fields and top-level language.

### Documentation
- Consolidated P0/P1/nonfunctional checklists into `docs/development/specs/REQUIREMENTS.md`.
- Archived legacy spec files and updated references to the consolidated requirements.
- Marked `docs/development/research/RESEARCH_LOG.md` as historical reference-only.
- Updated doc index/status to reflect specs and research locations.

## 2026-01-04 - Service Boundary + CVSS Split

### CLI
- Moved CI execution core into `cihub.services` with CLI adapter delegation.
- Added Trivy CVSS threshold outputs for workflow inputs.
- Added `cihub hub-ci trivy-install` for workflow-managed Trivy setup.
- Added Docker Compose runner for `run_docker` (optional health check + logs).
- Added `cihub report aggregate --details-output` and `--include-details` for per-repo detail summaries.
- Added `CIHUB_DEBUG` env toggle for opt-in developer tracebacks and debug context.
- Added `CIHUB_VERBOSE` env toggle for streaming tool output plus persisted tool logs.
- Added `CIHUB_DEBUG_CONTEXT` env toggle for opt-in CLI context blocks (ci/report build/aggregate).
- Added `cihub triage` to emit triage bundles (`triage.json`, `priority.json`, `triage.md`, `history.jsonl`).
- Added `CIHUB_EMIT_TRIAGE` env toggle for automatic triage emission after `cihub ci`.

### Config
- Added `thresholds.trivy_cvss_fail` and `python.tools.trivy.fail_on_cvss`.
- Added `python.tools.bandit.fail_on_medium` and `python.tools.bandit.fail_on_low` gates.
- Added hub CI bandit gate toggles (`hub_ci.tools.bandit_fail_high/medium/low`).
- Documented normalize-only config pipeline for workflow input generation.
- Added Python docker config fields (`compose_file`, `health_endpoint`, `health_timeout`) for parity with Java.
- Added `codeql.fail_on_error`, `docker.fail_on_error`, and `docker.fail_on_missing_compose` gates for strict failure control.

### Workflows
- Added `trivy_cvss_fail` input to `python-ci.yml` and passthrough from `hub-ci.yml`.
- Install Trivy in `python-ci.yml`/`java-ci.yml` when `run_trivy` is enabled.
- Wired hub CI bandit severity env toggles into `hub-production-ci.yml`.
- Run CodeQL in `python-ci.yml`/`java-ci.yml` when `run_codeql` is enabled (SARIF upload via CodeQL action).
- `hub-orchestrator.yml` can write and upload `hub-report-details.md` and optionally embed per-repo details in the summary.
- Defaulted `hub-orchestrator.yml` `include_details` to true for manual runs.
- Added workflow inputs/env passthrough for debug/verbose/triage toggles and triage/log artifacts in CI uploads.
- `hub-run-all.yml` installs Trivy and runs CodeQL actions when toggles are enabled, and can emit `hub-report-details.md`.
 
### Aggregation
- Mark missing report artifacts as `missing_report` so summaries show `MISSING` instead of empty metrics.

### Docs
- Updated ADRs and workflow docs for split CVSS thresholds and services boundary.

## 2026-01-03 - Workflow CLI Consolidation

### CLI
- Added hub workflow helper commands under `cihub hub-ci` (actionlint install/run, syntax checks, repo/source checks, security scans, CodeQL build, Kyverno helpers, smoke-test helpers, release tag helpers).
- Added `cihub hub-ci zizmor-run` to generate SARIF with an empty fallback on failure (no-inline compliance).
- `cihub hub-ci badges` now respects `hub_ci.tools` toggles and emits deterministic `disabled` badges for disabled tools.
- Security helpers now warn and set tool_status when a tool fails without valid output.
- `cihub sync-templates --check/--dry-run` skips gracefully with a warning when no GitHub token is available.
- Added services layer wrappers for CI runs, config helpers, and report summaries (`cihub.services.*`).
- Added `scripts/cli_command_matrix.py` to list/run guide-aligned CLI command checks.

### Config
- Allow shorthand booleans for tool configs and normalize at load boundaries to preserve defaults.
- Consolidated config loader I/O/merge to shared utilities.
- Added `thresholds_profile` presets with explicit overrides via `thresholds`.
- Expanded shorthand booleans to enabled sections (reports, notifications, kyverno, optional features, hub_ci).

### Workflows
- Removed all multi-line `run: |` blocks; workflows now call CLI helpers for logic.
- hub-security, smoke-test, kyverno, release, and hub-production workflow steps now delegate parsing/validation to CLI commands.
- Simplified python-ci/java-ci workflow headers to point at generated CONFIG docs.
- `hub-run-all.yml` summary job now honors `CIHUB_WRITE_GITHUB_SUMMARY`.
- `hub-production-ci.yml` pins actionlint to v1.7.4 for deterministic runs.

### Docs
- Config reference now renders shorthand tool types as `boolean|object`.
- Updated ADRs and guides for service-layer APIs and command-matrix validation.

## 2026-01-02 - Java SBOM Support

### CLI
- Added `java.tools.sbom` support in config loading and report summaries.
- Added syft-based SBOM generation in `cihub ci` (format configurable).
- `cihub hub-ci badges` now runs natively (no scripts dependency).
- Added `cihub hub-ci badges-commit` to commit badge updates (no-inline workflow compliance).
- `cihub ci` warns when reserved optional feature toggles are enabled.
- `cihub ci` can read notification env-var names from config (secrets still in env).
- `cihub report summary` only prints to stdout when `--write-github-summary` is enabled or an output path is provided.

### Config
- Added defaults for `repo.dispatch_enabled`, `repo.force_all_tools`, and `python.tools.sbom.enabled`.
- Added notification env-var name fields for Slack/email settings.

### Docs
- Updated guides and Makefile targets to use CLI replacements for deprecated scripts.

### Workflows
- **hub-ci.yml** now passes `run_sbom` to Java jobs.
- **java-ci.yml** accepts `run_sbom` and wires `CIHUB_RUN_SBOM`.
- **hub-production-ci.yml** gates jobs via `cihub hub-ci outputs` and uses hub-ci thresholds for coverage/mutation.
- **hub-production-ci.yml** generates and commits badges via CLI commands (no inline shell).

## 2026-01-01 - Summary Commands + Snapshot Tests

### CLI
- Added `cihub report security-summary` (modes: repo, zap, overall) for hub-security.yml summaries.
- Added `cihub report smoke-summary` (modes: repo, overall) for smoke-test.yml summaries.
- Added `cihub report kyverno-summary` for kyverno-ci.yml and kyverno-validate.yml summaries.
- Added `cihub report orchestrator-summary` (modes: load-config, trigger-record) for hub-orchestrator.yml summaries.
- All summary commands honor `CIHUB_WRITE_GITHUB_SUMMARY` env var and `--write-github-summary`/`--no-write-github-summary` flags.
- Summary commands no longer print to stdout when the summary toggle disables output.

### Tests
- Added `tests/test_summary_commands.py` with 19 snapshot tests covering all summary commands.
- Tests verify output format parity with old inline heredocs.
- Added toggle audit tests verifying `CIHUB_WRITE_GITHUB_SUMMARY` env var behavior.

### Workflows
- **hub-security.yml**: Replaced inline matrix build with `cihub discover`, replaced inline summaries with CLI commands.
- **smoke-test.yml**: Replaced inline summaries with `cihub report smoke-summary`.
- **kyverno-ci.yml** and **kyverno-validate.yml**: Replaced inline summaries with `cihub report kyverno-summary`.
- **hub-orchestrator.yml**: Replaced inline summaries with `cihub report orchestrator-summary`.
- All workflows now use `CIHUB_WRITE_GITHUB_SUMMARY` env var for toggle control.

## 2026-01-01 - No-Inline Workflow Cleanup

### CLI
- Added `cihub dispatch trigger` to dispatch workflows and poll for run ID (replaces inline JS in hub-orchestrator.yml).
- Added `cihub dispatch metadata` to generate dispatch metadata JSON files (replaces heredoc in hub-orchestrator.yml).
- Added `cihub report dashboard` to generate HTML or JSON dashboards from aggregated reports.
- Added CLI env overrides for tool toggles (e.g., `CIHUB_RUN_PYTEST=true`) and summary toggle (`CIHUB_WRITE_GITHUB_SUMMARY=false`).

### Workflows
- **hub-orchestrator.yml**: Removed 90+ lines of inline JavaScript, now uses `cihub dispatch trigger` and `cihub dispatch metadata`.
- **config-validate.yml**: Updated to use `cihub hub-ci validate-configs` and `cihub hub-ci validate-profiles`.
- **python-ci.yml**: Fixed typo in artifact name (`arme tifact_prefix` → `artifact_prefix`).

### Scripts (Deprecated)
- Converted `scripts/aggregate_reports.py` to deprecation shim → use `cihub report dashboard`.

### Tests
- Updated `test_aggregate_reports.py` to import from `cihub.commands.report` instead of deprecated shim.
- Tests now use 3-tuple return (reports, skipped, warnings) matching new API.

## 2025-12-31 - Phase 4: Remaining Scripts → CLI

### CLI
- Added `cihub config apply-profile --profile <path>` to apply profile defaults to repo configs.
- `cihub config apply-profile` now supports `--target` and `--output` for arbitrary file paths (parity with deprecated script).
- Added `cihub hub-ci verify-matrix-keys` to verify hub-run-all.yml matrix references match discover.py output.
- Added `cihub hub-ci quarantine-check [--path <dir>]` to fail if any file imports from `_quarantine`.

### Scripts (Deprecated)
- Converted `scripts/apply_profile.py` to deprecation shim → use `cihub config apply-profile`.
- Converted `scripts/verify_hub_matrix_keys.py` to deprecation shim → use `cihub hub-ci verify-matrix-keys`.
- Converted `scripts/check_quarantine_imports.py` to deprecation shim → use `cihub hub-ci quarantine-check`.

### Workflows
- Updated `hub-production-ci.yml` to use CLI commands instead of deprecated scripts.

### Tests
- Updated `test_apply_profile.py` and `test_templates.py` to import from `cihub.config.merge` and `cihub.config.io` instead of deprecated shims.

## 2025-12-31 - Badge CLI Integration

### CLI
- Added `cihub hub-ci badges` to generate or validate badge JSON from workflow artifacts.

## 2025-12-31 - Summary Toggle + Report Validation Consolidation

### CLI
- `cihub ci` now defaults `GITHUB_STEP_SUMMARY` behavior from `reports.github_summary.enabled` and supports `--no-write-github-summary`.
- `cihub report validate` now accepts `--summary`, `--reports-dir`, and `--debug` for summary/artifact cross-checks.

### Workflows
- `hub-ci.yml` now passes `write_github_summary` to language workflows.
- `python-ci.yml` and `java-ci.yml` pass `--write-github-summary`/`--no-write-github-summary` based on inputs.

### Scripts
- Deprecated `scripts/validate_summary.py` now delegates to `cihub report validate`.

## 2025-12-31 - Hub Aggregation Moved Into CLI

### CLI
- Added `cihub report aggregate` for hub orchestrator aggregation.
- Added `cihub report aggregate --reports-dir` for hub-run-all aggregation without GitHub API access.
- Deprecated `scripts/run_aggregation.py` (shim now delegates to CLI).

### Workflows
- `hub-orchestrator.yml` now calls `python -m cihub report aggregate` instead of inline Python.

## 2025-12-31 - Workflow Contract Verification

### CLI
- Added `cihub verify` to validate caller templates and reusable workflow inputs match.
- `make verify` now runs the contract check before syncing templates.
- Added `cihub verify --remote` (template drift via GitHub API) and `--integration` (clone + run `cihub ci`).
- Added `make verify-integration` for a full integration sweep.

### Tests
- Added workflow contract tests to prevent template/workflow drift.

## 2025-12-31 - Workflow Security & Verification Fixes

### Security
- **Fixed template-injection vulnerabilities in workflows** - Converted `${{ inputs.* }}` to environment variables in `python-ci.yml`, `java-ci.yml`, and `kyverno-ci.yml` to prevent potential command injection.
- **Enhanced zizmor CLI handler** - Added `_run_zizmor()` function in `check.py` with:
  - `--min-severity high` filtering (mirrors bandit pattern)
  - Auto-fix detection with helpful 💡 suggestions
  - Direct link to remediation docs

### Bug Fixes
- **Fixed smoke --full test failure** - Added `pythonpath = ["."]` to scaffold template `pyproject.toml` so pytest can find local modules.
- **Fixed gitleaks false positives** - Updated `.gitleaksignore` with correct fingerprints for test file API key patterns.
- **Fixed broken docs links** - Updated sigstore URLs in `KYVERNO.md` and `ADR-0012` (old `/cosign/keyless/` → `/cosign/signing/overview/`).

### CLI Improvements
- `cihub check` now displays suggestions with 💡 emoji for failed checks that have remediation guidance.

## 2025-12-31 - Pre-push Verify + Tool Installation

### Developer Workflow
- Added `make verify` to run full pre-push validation (`cihub check --all --install-missing --require-optional`) plus template drift check.
- Added `--install-missing` and `--require-optional` flags to `cihub check` to prompt for installing optional tools and fail if they are missing.
- Added `zizmor` to dev dependencies for local workflow security scanning.
- Fixed smoke validation by adding `thresholds.max_*` fields to the schema and ensuring CI tool execution prefers the active venv.

## 2025-12-30 - Formatter Unification (Ruff-only)

### Breaking Changes
- **Removed Black from `cihub check`** - Ruff format is now the single source of truth for local formatting

### Rationale
- Eliminates formatter conflicts (Ruff and Black can disagree on edge cases)
- Faster formatting (Ruff is 10-100x faster than Black, written in Rust)
- Unified tooling: Ruff handles both linting and formatting

### Notes
- CI workflows still run Black until `hub-production-ci.yml` is updated.
- `cihub check` now invokes mypy/pytest via the current Python interpreter to honor the active environment.

### Migration
- Run `make format` (or `ruff format cihub/ tests/ scripts/`) to format code
- Keep Black installed if CI still enforces it.

## 2025-12-30 - Template Freshness Guard

### Templates & Tests
- Archived legacy dispatch templates to `templates/legacy/`
- Updated docs/tests to reference caller templates under `templates/repo/`
- Added a guard to prevent legacy dispatch templates from drifting in active paths
- Added `.yamllint` config to align linting with 120-char line length and ignore archived templates

## 2025-12-30 - CLI Doc Drift Guardrails & Plan Consolidation

### CLI & Tooling
- Added `cihub docs generate/check` to auto-generate reference docs from CLI and schema.
- Added CLI helpers for local verification: `preflight`/`doctor`, `scaffold`, and `smoke`.
- Added `cihub check` to run the full local validation suite (lint, typecheck, tests, actionlint, docs drift, smoke).
- Added tests for new CLI commands (docs/preflight/scaffold/smoke/check).
- Added pre-commit hooks for actionlint, zizmor, and lychee link checking.

### Documentation & Governance
- Added canonical plan: `docs/development/MASTER_PLAN.md`.
- Added reference-only banners to `pyqt/planqt.md` and archived `docs/development/archive/ARCHITECTURE_PLAN.md`.
- Updated ADRs to reflect `hub-ci.yml` wrapper and CLI-first verification.
- Refreshed `docs/development/status/STATUS.md`.
- Rewrote the audit ledger as `docs/development/archive/audit.md`.
- Generated `docs/reference/CLI.md` and `docs/reference/CONFIG.md` from code.

## 2025-12-26 - Security Hardening & Boolean Config Fix

### Security Fixes (OWASP Audit)
- **H1: GitHub Actions Expression Injection** - Fixed in `hub-orchestrator.yml` by passing matrix values through environment variables instead of direct `${{ }}` interpolation in JavaScript
- **H2: XXE Vulnerability** - Added `defusedxml` dependency for safe XML parsing in CLI POM detection
- **H3: Path Traversal** - Added `validate_repo_path()` and `validate_subdir()` functions in `cihub/cli.py`
- **H6: Force Push Confirmation** - Added interactive confirmation for v1 tag force-push in `cihub sync-templates --update-tag`
- **M3: Subdir Path Traversal** - Added `..` detection in `hub-run-all.yml` before cd into subdir
- **Shell Injection** - Fixed `hub-security.yml` to pass `inputs.repos` via environment variable

### Boolean Config Type Coercion Fix
- **Fixed summary table "Ran" column** - `java-ci.yml` lines 582-590 now use boolean comparison (`== true`) instead of string comparison (`== 'true'`)
- **Added ADR-0028** - Documents boolean type coercion through YAML → Python → GITHUB_OUTPUT → JavaScript → workflow_dispatch → workflow inputs

### Documentation
- Updated ADR README with ADRs 0023-0028
- Added ADR-0028: Boolean Config Type Coercion

## 2025-12-26 - Workflow Shellcheck Cleanup

### Workflows
- Refactored summary output blocks to avoid shellcheck SC2129 warnings across hub workflows.
- Grouped multi-line `GITHUB_OUTPUT` writes to prevent shellcheck parse errors.
- Cleaned up summary generation redirections in hub, security, smoke test, and kyverno workflows.

## 2025-12-26 - Docs Reorg, Fixtures Expansion, CLI Hardening

### Documentation & Governance
- Reorganized development docs into status/architecture/execution/research/archive subfolders.
- Renamed and aligned plan docs to `ARCHITECTURE_PLAN.md` (now archived) and `STATUS.md`.
- Folded fixtures plan into smoke test guide; archived legacy plans and snapshots.
- Refreshed root README and added .github/CONTRIBUTING.md, .github/SECURITY.md, .github/CODE_OF_CONDUCT.md.
- Updated doc indexes and references after reorg.
- Added root Makefile + command matrix for consistent developer workflows.
- Moved CHANGELOG/BACKLOG/DEVELOPMENT into `docs/development/` to reduce root clutter.

### Fixtures & Integration
- Expanded fixture configs (gradle, setup.py, monorepo, src-layout) and added heavy-tool fixtures.
- Added CLI integration runner and updated smoke test guide with the full fixture matrix.

### CLI & Config
- Hardened config merging and profile loading; wizard cancellation handling.
- Normalized CLI output and moved config helpers out of cli.py.
- Config commands now reject unknown tools per language and keep YAML output clean (status to stderr).

### Workflows & CI
- Fixed shell usage in workflows and heredoc usage in python-ci.yml.
- Pinned zizmor install and aligned CI ignore patterns for coverage artifacts.
- Java CI summary now compares boolean inputs correctly.

### Testing
- Added targeted tests for POM parsing, secrets setup, and config command behavior.

## 2025-12-25 - Hub Production CI & Security Hardening

### Workflow Rename
- **Renamed `hub-self-check.yml` → `hub-production-ci.yml`** - Comprehensive production-grade CI for the hub itself

### CLI Config & Wizard Foundations
- Added schema loader/validator in `cihub/config/schema.py` and wired CLI validation to it
- Added wizard scaffolding (styles, validators, questions, summary, core runner)
- Extracted CLI command handlers into `cihub/commands/*` and added wrappers in `cihub/cli.py`
- Added new hub-side commands: `cihub new` and `cihub config` (edit/show/set/enable/disable)
- Updated NEW_PLAN acceptance checklist to require explicit CI summaries and failure context
- Added ADR-0027 documenting hub production CI policy

### Security Hardening
- All GitHub Actions pinned to SHA (supply chain security)
- Added `harden-runner` to all jobs (egress monitoring)
- Added least-privilege `GITHUB_TOKEN` permissions per job
- Trivy pinned to v0.31.0 (was @master)
- Fixed syntax check to properly validate all `cihub/**/*.py` files
- Pinned CodeQL actions to v4 SHA in hub/security/reusable workflows

### New CI Stages
- **Stage 0: Workflow Security** - actionlint + zizmor for workflow validation
- **Stage 5: Supply Chain** - OpenSSF Scorecard + Dependency Review
- SARIF uploads for Trivy, zizmor, and Scorecard findings
- Updated CI summary table with check descriptions and explicit results
- Forced ruff to respect exclusions in CI (skips `_quarantine`)
- Pip-audit now scans requirements files (avoids editable package false positives)

### Documentation
- Updated README and WORKFLOWS.md to reference `hub-production-ci.yml`
- Added Elastic License 2.0

## 2025-12-24 - ADR-0024 Threshold Resolution

### Reusable Workflows
- Removed `threshold_overrides_yaml`; thresholds now resolve from `.ci-hub.yml` and hub defaults via the CLI (config-only).
- Exported effective thresholds (`eff_*`) and wired all gates/summaries to use them (coverage, mutation, OWASP/Trivy, Semgrep, PMD, lint).
- Updated Java `report.json` to emit effective thresholds instead of raw inputs; summaries now show effective values.

### Orchestrator / Contract
- Kept dispatch inputs minimal; thresholds flow from config only per ADR-0024.
- Added ADR-0024 (`docs/adr/0024-workflow-dispatch-input-limit.md`) to document the 25-input limit strategy and single-override approach.

### Caller Templates
- Templates aligned with simplified callers; no `threshold_overrides_yaml` input required.

## 2025-12-24 - Quarantine System, NEW_PLAN, and CLI/Validation Hardening

### Architecture & Governance
- Added `_quarantine/` with phased graduation, `INTEGRATION_STATUS.md`, and `check_quarantine_imports.py` guardrail to prevent premature imports.
- Added `docs/development/archive/ARCHITECTURE_PLAN.md` (proposed self-validating CLI + manifest architecture); noted current blockers in the plan.

### CLI & Validation
- Added `setup-nvd` command; hardened `setup-secrets` token handling and cross-repo verification.
- Added template sync command/guard; validator fixes for summary drift and matrix key validation; wired Java POM checks into `cihub init`.
- Added CLI integration tests and correlation tests.

### Workflows & OWASP/NVD
- Fixed NVD/OWASP handling (use_nvd_api_key toggle, pass tokens) in central/reusable workflows; cleaned up workflow errors (duplicate keys, NameError).
- Note: the `setup-nvd`/NVD integration script still needs a follow-up fix; current version may not work end-to-end.

### Templates/Docs/Schema
- Updated caller templates and docs (TOOLS, WORKFLOWS, CONFIG.md) alongside ADR updates; minor schema/report tweaks to match governance changes.

## 2025-12-23 - CLI Dispatch Token Handling

### CLI (cihub)
- Trim whitespace from PAT input and reject tokens that contain embedded whitespace
- `setup-secrets` now sends the raw token to `gh` (no trailing newline)
- Added optional `--verify` preflight to confirm token validity before setting secrets

## 2025-12-19 - Property-Based Testing Support

### Hypothesis (Python)
- **New `run_hypothesis` input** (boolean, default: `true`) - Enable Hypothesis property-based testing
- **Pass/fail gate** - Property tests fail the build if any test fails
- **Example count tracking** - Shows "Hypothesis Examples: N" in Build Summary
- **Installed automatically** - `hypothesis` package added when running pytest

### jqwik (Java)
- **New `run_jqwik` input** (boolean, default: `false`) - Enable jqwik property-based testing
- **Integrated with Maven** - jqwik tests run via JUnit 5 during normal test phase
- **Property test count tracking** - Shows "jqwik Property Tests: N" in Build Summary
- **Pass/fail gate** - Property test failures fail the Maven build

### Template Updates
- Both `hub-python-ci.yml` and `hub-java-ci.yml` caller templates updated with matching inputs
- Pushed to `ci-cd-hub-fixtures` and `java-spring-tutorials` repos

### Docker Inputs Removed from CI Templates
- **Removed from workflow_dispatch**: `run_docker`, `docker_compose_file`, `docker_health_endpoint`
- **Reason**: GitHub limits workflow_dispatch to 25 inputs; Docker testing is a separate concern
- **Future**: Separate `hub-java-docker.yml` and `hub-python-docker.yml` templates planned
- **Note**: Trivy scanning (`run_trivy`) still works - it doesn't require Docker inputs
- **Reusable workflows still accept these inputs** - repos can hardcode in `with:` block if needed

---

## 2025-12-19 - Job Summary Improvements & Multi-Module Support

### Configuration Summary
- **Configuration Summary at top of job output** - Shows all enabled tools, thresholds, and environment settings at a glance
- **Project type detection** - Shows "Single module" or "Multi-module (N modules)" for Java projects
- **Workdir display** - Shows `. (repo root)` when workdir is "."

### Multi-Module Maven Support
- **JaCoCo aggregation** - Automatically finds and aggregates coverage from all modules' `jacoco.xml` files
- **PITest aggregation** - Automatically finds and aggregates mutation scores from all modules' `mutations.xml` files
- **Per-module breakdown** - Shows coverage/mutation score for each module (only when >1 module)
- **Backwards compatible** - Single-module projects work unchanged

### Lint Summary Improvements
- **Consistent table format** - All tools show in markdown table with Status/Issues/Max Allowed columns
- **Disabled reason shown** - When a tool is disabled, shows why (e.g., `run_ruff=false`)
- **Fixed empty values** - All values default to 0 to prevent display issues

### Mutation Testing Fixes (Python)
- **mutmut 3.x compatibility** - Fixed deprecated CLI options (`--paths-to-mutate`, `--runner`)
- **Result parsing** - Parse emoji output (🎉 = killed, 🙁 = survived) instead of `mutmut results`
- **Auto config** - Creates temp `setup.cfg` with mutmut config if not present

### New Java Inputs
- Added `max_checkstyle_errors` threshold
- Added `max_spotbugs_bugs` threshold
- Updated caller templates to include new inputs

---

## 2025-12-18 - Schema 2.0 & Reusable Workflow Migration

### Schema 2.0 Report Format
- **Aggregator upgraded for schema 2.0** - Now extracts `tool_metrics`, `tools_ran`, and `tests_passed`/`tests_failed` from reports
- **Added `--schema-mode` flag** - Supports `warn` (default, includes all reports with warning) and `strict` (skips non-2.0 reports, exits 1 if any skipped)
- **New helper functions** - `detect_language()` detects Java/Python from report fields, `get_status()` handles both build/test status fields
- **HTML dashboard enhanced** - Added Language and Tests columns to repository table
- **Comprehensive test coverage** - 28 tests covering helpers, load_reports modes, summary generation, and HTML output

### Orchestrator Migration
- **Dispatch defaults changed to hub-*-ci.yml** - Orchestrator now defaults to reusable workflow callers (`hub-python-ci.yml`/`hub-java-ci.yml`)
- **All repo configs updated** - Explicit `dispatch_workflow` field in all configs (fixtures use new callers, smoke-tests/bst-demo/java-spring use old names until migrated)

### New Files
- `scripts/validate_report.sh` - Bash script for validating report.json against schema 2.0 requirements
- `docs/adr/0019-report-validation-policy.md` - ADR documenting fixture validation strategy (passing vs failing, expect-clean)
- `docs/adr/0020-schema-backward-compatibility.md` - ADR documenting schema migration strategy and --schema-mode flag

### Unreleased (from CHANGES.md)
- Replaced `hub-run-all.yml` matrix builder with `scripts/load_config.py` to honor `run_group`, dispatch toggles, and all tool flags/thresholds from schema-validated configs
- Added `scripts/verify_hub_matrix_keys.py` to fail fast when workflows reference matrix keys that the builder does not emit
- Hardened reusable workflows: Java/Python CI now enforce coverage, mutation, dependency, SAST, and formatting gates based on run_* flags and threshold inputs
- Stabilized smoke test verifier script (no early exit, no eval) and anchored checks for workflow/config presence
- Added `hub-self-check` workflow (matrix verifier, smoke setup check, matrix dry-run) and unit tests for config loading/generation
- Installed `jq` in reusable workflows and reordered gates to upload artifacts even when enforcement fails

---

## 2025-12-15 (Night)

### Bug Fixes
- **Fixed PITest mutation score showing 0%** - PITest XML uses single quotes (`status='KILLED'`) but grep patterns were looking for double quotes (`status="KILLED"`). Updated regex to match both quote styles: `grep -cE "status=['\"]KILLED['\"]"`
- **Fixed PITest module detection** - Now skips `template` directories that have pom.xml with pitest but aren't actual Maven modules
- **Added debug output** for mutation aggregation to show which mutations.xml files are found and their scores
- Fixed in: `hub-run-all.yml`, `java-ci.yml`, `java-ci-dispatch.yml` (template and fixtures)

### Repository Cleanup
- Added `artifacts/` to `.gitignore` and removed from git tracking
- Added `hub-fixtures/` and `ci-cd-hub-fixtures/` to `.gitignore` (cloned fixture repos)

---

## 2025-12-15 (Evening)

### Bug Fixes
- Fixed SpotBugs, Checkstyle, PMD not running on repos without `mvnw` - added `mvn` fallback
- Fixed mutmut 0% mutation score - tools now properly detect mutations

### Hub Self-Check Workflow
- Added `hub-self-check.yml` workflow that runs on push/PR to validate hub integrity
- Jobs: syntax-check, unit-tests, validate-templates, validate-configs, verify-matrix-keys
- Runs automatically when scripts, tests, templates, config, or schema files change

### Test Coverage
- Added `tests/test_templates.py` with 70 tests validating all templates against schema
- Tests verify profile merging, dispatch template validity, and no stale repo name references
- Total test count: 109 (39 original + 70 new)

### Tool Defaults
- Enabled ALL tools by default in Java dispatch template (pitest, semgrep, trivy, codeql)
- Enabled ALL tools by default in Python dispatch template (mypy, mutmut, semgrep, trivy, codeql)
- Updated fixture dispatch workflows to match with comprehensive tool status in summaries

### Fixture Enhancements
- Added `requirements.txt` to Python fixtures for pip-audit scanning
- Updated workflow summaries to show all 12 tools with status indicators (✅ Ran / ⏭️ Skipped)
- Temporarily disabled contact-suite-spring config (900 tests, too slow for testing)

### Cross-Repo Authentication
- Added HUB_DISPATCH_TOKEN support for downloading artifacts from dispatched workflow runs
- Required for orchestrator to aggregate reports across repositories

---

## 2025-12-15

### Repository Rename
- Renamed repository from `ci-hub-orchestrator` to `ci-cd-hub`
- Updated all workflow files, documentation, and scripts with new repo name
- Updated git remote URLs and documentation cross-references

### Fixture Enhancement (Comprehensive Tool Testing)
- Enhanced all Python fixtures (`python-passing`, `python-failing`) with rich, mutable code including 20+ math functions with conditionals, loops, type hints
- Enhanced all Java fixtures (`java-passing`, `java-failing`) with comprehensive Calculator classes
- Enabled ALL tools in fixture configs: pytest, ruff, black, isort, bandit, pip-audit, mypy, mutmut, hypothesis, semgrep (Python); checkstyle, spotbugs, owasp, pmd, pitest, semgrep (Java)
- Added intentional bugs and security issues to `*-failing` fixtures for tool detection validation

### Mutmut 3.x Compatibility
- Fixed mutmut invocation for 3.x CLI (removed deprecated `--paths-to-mutate` and `--runner` flags)
- Added `[tool.mutmut]` configuration to fixture `pyproject.toml` files with `paths_to_mutate` and `tests_dir` settings
- mutmut 3.x now uses config file instead of command-line arguments

### Workflow Improvements
- Fixed "Invalid format" errors in GitHub Actions output parsing
- Replaced `grep ... || echo 0` patterns with `${VAR:-0}` default value fallbacks
- Used lookahead regex patterns (`\d+(?= passed)`) for more robust test count extraction
- Added `tail -1` to ensure only final summary line is captured

### Documentation Cleanup
- Removed stale `docs/analysis/scalability.md` (old brainstorm doc)
- Fixed duplicate Kyverno entries in `docs/README.md`
- Added `docs/development/audit.md` to `.gitignore`

## 2025-12-14
- Added docs/development/specs/ with P0, P1, and nonfunctional checklists.
- Replaced STATUS.md with a concise execution checklist linking to requirements.
- Added doc stubs extracted from the old plan: WORKFLOWS, CONFIG.md, TOOLS, TEMPLATES, MODES, TROUBLESHOOTING, ADR index.
- Updated AGENTS to reflect current focus on P0 execution.
- Linked ROADMAP to requirements and noted planned phases.
- Hardened `hub-orchestrator.yml`: pass computed inputs, honor `default_branch`, set dispatch permissions, attempt run-id capture, emit dispatch metadata artifacts, and generate a hub summary/report from dispatch results.
- Added schema validation in orchestrator config load (jsonschema) to fail fast on bad repo configs; compiled scripts to ensure Python syntax.
- Captured dispatch metadata as artifacts for downstream aggregation; summaries now include per-repo dispatch info.
- Implemented aggregation pass to poll dispatched runs, fail on missing/failed runs, download `ci-report` artifacts when present, and roll up coverage/mutation into `hub-report.json`.
- Added schema validation to `scripts/load_config.py`; added `jsonschema` dependency to `pyproject.toml`.
- Added copy/paste templates: `templates/repo/.ci-hub.yml` and `templates/hub/config/repos/repo-template.yaml`.
- Added `config-validate` workflow to run schema validation on config/schema changes and PRs.
- Added ADR-0001 (Central vs Distributed) and expanded docs (CONFIG.md, TOOLS, MODES, TROUBLESHOOTING, TEMPLATES).
- Fixed orchestrator config validation indentation bug and added dispatch run-id polling backoff/timeout.
- Added ADRs 0002-0005 (config precedence, reusable vs dispatch, aggregation, dashboard).
- Rewrote ADRs 0003-0006 to match actual implementation: ADR-0003 now accurately documents github-script dispatch mechanism; ADR-0004 now shows actual hub-report.json schema (runs[] array, not object); ADR-0005 added for Dashboard Approach (GitHub Pages); ADR-0006 added for Quality Gates and Thresholds.
