# CI/CD Hub - Master Plan

**Status:** Canonical plan for all active work
**Last Updated:** 2026-01-05

> This is THE plan. All action items live here. STATUS.md tracks current state.

---

## Purpose

Single source of truth for what we are doing now. Other docs can provide depth, but this file owns priorities, scope, and sequencing.

---

## v1.0 Cutline

> **What must ship for v1.0 vs what is explicitly deferred.**
> Items below the cutline move to "Post v1.0 Backlog" at the end of this document.

### Quick Wins (Do First)

**CLI Commands:**
- [ ] `cihub docs stale` — Detect stale code references in docs (design in `active/DOC_AUTOMATION_AUDIT.md`)
- [ ] `cihub docs audit` — Doc lifecycle consistency checks
- [ ] `cihub config validate` — Validate hub configs
- [ ] `cihub audit` — Umbrella command (docs check + links + adr check + config validate)
- [ ] `--json` flag for all commands including hub-ci subcommands

**Documentation:**
- [ ] Generate `docs/reference/TOOLS.md` from `cihub/tools/registry.py`
- [ ] Generate `docs/reference/WORKFLOWS.md` from `.github/workflows/*.yml`
- [ ] Plain-text reference scan for stale `docs/...` strings
- [ ] Universal header enforcement for manual docs
- [ ] `.cihub/tool-outputs/` artifacts for doc automation
- [ ] Tooling integration checklist: toggle -> CLI runner (no inline workflow logic) -> tool-outputs -> report summaries/dashboards -> templates/profiles -> docs refs -> template sync tests

**Clean Code:**
- [ ] `_tool_enabled()` consolidation (5 implementations → 1)
- [ ] Gate-spec refactor (table-driven, ~100 lines)
- [ ] Language strategy extraction (Python/Java)
- [ ] Expand CI-engine tests (2 → 20+)
- [ ] Output normalization (forbid `print()` in commands)

**Security/CI Hygiene:**
- [ ] Pin `step-security/harden-runner` versions (21 uses)
- [ ] Standardize all action version pins

### Heavy Lifts (After Quick Wins)

- [ ] Env/context wrapper (`GitHubContext` for 17 `GITHUB_*` reads)
- [ ] Runner/adapter boundaries (subprocess only in `ci_runner/`)
- [ ] "No inline logic" workflow guard
- [ ] Performance guardrails for docs stale/audit (<5s on ~28k corpus)

### Verification (Final Step)

- [ ] Re-run hub production workflows after all v1.0 changes
- [ ] Record smoke test + pytest results in STATUS.md

---

## Current Focus (ADR-0035)

- [x] Implement triage bundles + priority output + LLM prompt pack (behind `CIHUB_EMIT_TRIAGE` env toggle).
- [ ] Implement registry CLI + versioning/rollback.
- [x] Make aggregate reports resilient to failed repos (render partial summaries instead of aborting).
- [x] Implement `cihub report dashboard` (HTML + JSON output) replacing scripts/aggregate_reports.py.
- [x] Add CLI env overrides for tool toggles and summary toggle (`CIHUB_RUN_*`, `CIHUB_WRITE_GITHUB_SUMMARY`).
- [x] Add Java SBOM support (schema + CLI runner + workflow wiring).
- [x] Toggle audit + enforcement:
  - [x] Align defaults for `repo.dispatch_enabled`, `repo.force_all_tools`, and `python.tools.sbom.enabled`.
  - [x] Add notifications env-var names to schema/defaults and CLI.
  - [x] Warn when reserved optional feature toggles are enabled.
  - [x] Gate hub-production-ci jobs via `cihub hub-ci outputs`.
- [x] Ensure workflow toggles install required CLIs (Trivy) and wire bandit severity env toggles.
- [x] Implement `run_codeql`/`run_docker` execution (CodeQL actions in reusable workflows + docker-compose runner in `cihub ci`, with fail-on-error gates).
- [x] Align `hub-run-all.yml` with CodeQL/Trivy toggles and optional per-repo detail output.
- [x] Add `docker.fail_on_missing_compose` gate and mark missing report artifacts as `missing_report` in aggregation summaries.
- [x] Add optional per-repo detail output for orchestrator aggregation (`--details-output` + `--include-details`).
- [x] **No-inline workflow cleanup:**
  - [x] Wire summary toggle in `hub-run-all.yml` summary job (`CIHUB_WRITE_GITHUB_SUMMARY`).
  - [x] Replace zizmor SARIF heredoc in `hub-production-ci.yml` with `cihub hub-ci zizmor-run`.
  - [x] Remove all multi-line `run: |` blocks by moving logic into `cihub hub-ci` helpers.
  - [x] Summary commands implemented and wired:
    - `cihub report security-summary` (modes: repo, zap, overall)
    - `cihub report smoke-summary` (modes: repo, overall)
    - `cihub report kyverno-summary`
    - `cihub report orchestrator-summary` (modes: load-config, trigger-record)
  - [x] Snapshot tests in `tests/test_summary_commands.py` (19 tests) verify parity with old heredocs.
  - [x] Toggle audit tests verify `CIHUB_WRITE_GITHUB_SUMMARY` env var behavior.

## Canonical Sources of Truth

1. **Code** (`cihub/`, `schema/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is the authoritative interface documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the authoritative config contract.

## References (Background Only)

**Active Design Docs** (in-progress designs, listed in `status/STATUS.md`):
- `docs/development/active/CLEAN_CODE.md` (architecture improvements: polymorphism, encapsulation)
- `docs/development/active/DOC_AUTOMATION_AUDIT.md` (doc automation design: `cihub docs stale`, `cihub docs audit`)
- `docs/development/active/PYQT_PLAN.md` (PyQt concept scope)

**Architecture:**
- `docs/development/architecture/ARCH_OVERVIEW.md` (current architecture overview)
- `docs/development/archive/ARCHITECTURE_PLAN.md` (archived deep-dive plan)

These are references, not competing plans.

---

## Current Decisions

- **CLI is the execution engine**; workflows are thin wrappers.
- **Single entrypoint workflow is `hub-ci.yml`**; it routes to `python-ci.yml`/`java-ci.yml` internally.
- **Local verification uses CLI scaffolding + smoke**; fixtures repo is for CI/regression, not required for local tests.

---

## Near-Term Priorities (In Order)

### 1) Plan Consolidation (Immediate)

- [x] Create this file as the canonical plan.
- [x] Add reference banners to `docs/development/active/PYQT_PLAN.md` and `docs/development/archive/ARCHITECTURE_PLAN.md` stating this plan is canonical.

### 2) CLI as Source of Truth (Core)

- [x] Implement CLI helpers:
  - `cihub preflight` (doctor alias)
  - `cihub scaffold <type>`
  - `cihub smoke [--full]`
- [ ] Commit CLI helpers.
- [x] Add CLI doc generation commands:
  - `cihub docs generate` -> `docs/reference/CLI.md` + `docs/reference/CONFIG.md`
  - `cihub docs check` for CI drift prevention
- [x] Add `cihub check` command (local validation suite: preflight → lint → typecheck → test → actionlint → docs-check → smoke)
- [ ] Optional CLI utilities: see **6) CLI Automation** below

### 3) Documentation Cleanup (Controlled Sweep)

- [x] Create `docs/README.md` as index of canonical vs reference vs archive.
- [x] Merge overlapping guides into **one** user entry point:
  - `docs/guides/GETTING_STARTED.md` is canonical user entry point.
  - Folded in ONBOARDING, MODES, DISPATCH_SETUP (now archived with superseded banners).
  - MONOREPOS, TEMPLATES, KYVERNO kept as advanced references.
  - `docs/guides/TROUBLESHOOTING.md` kept separate.
- [x] Archive `CONFIG_REFERENCE.md` (superseded by generated `CONFIG.md`).
- [x] Archive `docs/development/architecture/ARCHITECTURE_PLAN.md`.
- [ ] Move remaining legacy/duplicate docs to `docs/development/archive/` with a superseded header (no deletion).
- [x] Archive legacy dispatch templates under `templates/legacy/` and update docs/tests to match.
- [ ] Make reference docs generated, not hand-written (CLI/CONFIG done; TOOLS/WORKFLOWS next).
  - [ ] Generate `docs/reference/TOOLS.md` from `cihub/tools/registry.py` via `cihub docs generate`.
  - [ ] Generate `docs/reference/WORKFLOWS.md` (triggers/inputs tables) from `.github/workflows/*.yml`.
  - Keep `guides/WORKFLOWS.md` narrative-only; tables go in generated reference.
  - Status docs: `development/status/STATUS.md` is single source for active design docs.
  - [x] Consolidate specs into `docs/development/specs/REQUIREMENTS.md` (P0/P1/nonfunctional archived).
  - [x] Mark `docs/development/research/RESEARCH_LOG.md` as historical reference.
  - Architecture docs: keep `docs/development/architecture/ARCH_OVERVIEW.md` as active reference.

### 4) Staleness Audit (Doc + ADR)

- [x] Run a full stale-reference audit (docs/ADRs/scripts/workflows). → See `status/STATUS.md`
- [x] Record findings in a single audit ledger (`docs/development/archive/audit.md`).
- [x] Update ADRs that reference old workflow entrypoints and fixture strategy.
- [x] Fix inaccurate config references (pytest.threshold, nvd_api_key_required).
- [x] Fix broken internal links (ARCH_OVERVIEW.md smoke test link).
- [ ] Add superseded banners to archive files (CONFIG_REFERENCE, DISPATCH_SETUP, MODES, ONBOARDING).
- [ ] Review ADR-0005 (Dashboard) status — still "Proposed" after 2+ weeks.
- [ ] Clarify ADR-0035 timeline — which features are v1 vs deferred.
- [ ] Add doc drift scan for plain-text `docs/...` references to catch stale mentions (wire into `cihub check --audit`).

### 5) Verification

- [x] Run targeted pytest and record results in `docs/development/status/STATUS.md`.
- [x] Run `cihub smoke --full` on scaffolded fixtures and capture results.
- [ ] Re-run the hub production workflows as needed after CLI changes.
- [x] Define and document a local validation checklist that mirrors CI (`cihub check` + `make check` + GETTING_STARTED.md section).
- [x] Capture a CI parity map in the plan (localizable vs CI-only per hub-production step).

### 6) CLI Automation (Drift Prevention)

- [x] Add pre-commit hooks: actionlint, zizmor, lychee
- [x] Fix stale doc links (TOOLS.md, TEMPLATES.md, TROUBLESHOOTING.md, DEVELOPMENT.md pointed to archived guides)
- [x] `cihub docs links` — Check internal doc links (offline by default, `--external` for web)
- [x] `cihub adr new <title>` — Create ADR from template with auto-number
- [x] `cihub adr list` — List all ADRs with status
- [x] `cihub adr check` — Validate ADRs reference valid files
- [x] `cihub verify` — Contract check for caller templates and reusable workflows (optional remote/integration modes)
- [x] `cihub hub-ci badges` — Generate/validate CI badges from workflow artifacts.
- [ ] `cihub config validate` (or `cihub validate --hub`) — Validate hub configs (resolves validate ambiguity)
- [ ] `cihub audit` — Umbrella: docs check + links + adr check + config validate
- [ ] `cihub docs stale` — Detect stale doc references via AST symbol extraction. Design: `active/DOC_AUTOMATION_AUDIT.md`
- [ ] `cihub docs workflows` — Generate workflow tables from `.github/workflows/*.yml` (replaces manual guides/WORKFLOWS.md)
- [ ] `cihub docs audit` — Doc lifecycle consistency checks (wire into `cihub check --audit`):
  - [ ] Every doc in `status/STATUS.md` Active Design Docs table must exist under `development/active/`
  - [ ] Every file under `development/active/` must be listed in STATUS.md
  - [ ] Files under `development/archive/` must have a superseded header
  - [ ] Path changes in `active/` or `archive/` require `docs/README.md` + `status/STATUS.md` updates in same diff
  - [ ] Validate MASTER_PLAN.md references only real paths (no active/ vs non-active mismatches)
  - [ ] Make targets referenced in docs exist in Makefile (CLI is the product; Make is a wrapper)
- [x] Add `make links` target
- [ ] Add `make audit` target
- [x] Add a "triage bundle" output for failures (machine-readable: command, env, tool output, file snippet, workflow/job/step). *(Implemented via `CIHUB_EMIT_TRIAGE`)*
- [x] Add a template freshness guard (caller templates + legacy dispatch archive).
  - [x] PR trigger on `template-guard.yml` (validate-local job runs tests/test_templates.py + test_commands_scaffold.py)
  - [x] Render-diff tests (`TestRenderCallerWorkflow`) verify CLI output matches templates
  - [x] Contract verification (`cihub verify`) added to `cihub check --full`
  - [x] Remote sync check (`sync-templates --check`) in `cihub check --full` (skips gracefully if no GH_TOKEN)
  - [x] All 5 scaffold types tested (python-pyproject, python-setup, java-maven, java-gradle, monorepo)

### 6b) Documentation Automation (Design: `active/DOC_AUTOMATION_AUDIT.md`)

> **Design doc:** Full requirements and architecture in `docs/development/active/DOC_AUTOMATION_AUDIT.md`

- [ ] `cihub docs stale` — Detect stale code references in docs:
  - [ ] Python AST symbol extraction (base vs head comparison)
  - [ ] Schema key path diffing
  - [ ] CLI surface drift detection (help snapshot comparison)
  - [ ] File move/delete detection (`--name-status --find-renames`)
  - [ ] Output modes: human, `--json`, `--ai` (LLM prompt pack)
- [ ] `cihub docs audit` — Doc lifecycle consistency checks:
  - [ ] Validate `active/` ↔ `STATUS.md` sync
  - [ ] Validate `archive/` files have superseded headers
  - [ ] Plain-text reference scan for `docs/...` strings
  - [ ] ADR metadata lint (Status/Date/Superseded-by)
  - [ ] Universal header enforcement for manual docs
  - [ ] Specs hygiene: only `REQUIREMENTS.md` is active under `development/specs/` with required header fields
- [ ] `.cihub/tool-outputs/` artifacts for doc automation:
  - [ ] `docs_stale.json` — Machine-readable stale reference report
  - [ ] `docs_stale.prompt.md` — LLM-ready prompt pack
  - [ ] `docs_audit.json` — Lifecycle/reference findings
- [ ] Doc manifest (`docs_manifest.json`) for LLM context:
  - [ ] Path, category (guide/reference/active/archived)
  - [ ] Generated vs manual flag
  - [ ] Last-reviewed date
- [ ] Generated references expansion:
  - [ ] `docs/reference/TOOLS.md` from `cihub/tools/registry.py`
  - [ ] `docs/reference/WORKFLOWS.md` from `.github/workflows/*.yml`

### 7) Local/CI Parity (Expand `cihub check`)

- [x] Define a CI-parity map: every hub-production-ci.yml step is either locally reproducible or explicitly CI-only.
- [x] Expand `cihub check` tiers:
  - `cihub check` (fast default)
  - `cihub check --audit` (docs links + ADR check + config/profile validation)
  - `cihub check --security` (bandit, pip-audit, gitleaks, trivy; skip if missing)
  - `cihub check --full` (audit + templates + verify-contracts + sync-templates-check + matrix keys + license + zizmor)
  - `cihub check --all` (everything)
- [x] Add optional tool detection and clear "skipped/missing tool" messaging.
- [x] Update `docs/guides/GETTING_STARTED.md` with new flags and expected runtimes.
- [x] Add `docs/guides/CLI_EXAMPLES.md` with runnable command examples.
- [ ] Evaluate `act` integration for local workflow simulation (document limitations; optional).

### 8) Services Layer (Phase 5A, PyQt6 Readiness)

- [x] Add discovery service + tests; wire `cihub discover` to services layer.
- [x] Add report validation service with **parity-first** behavior:
  - include summary parsing + summary/report cross-checks
  - include artifact fallback when metrics are missing
  - include effective-success merging for summary/tool status
  - avoid duplicate maps/logic between service and CLI
- [x] Wire `cihub report validate` to the service and keep CLI-only output/verbosity in the adapter.
- [x] Add aggregation service (Phase 5A pattern) and wire CLI adapter.
- [x] Add CI service wrapper for GUI/programmatic access (`cihub.services.ci`).
- [x] Add config service helpers for load/edit operations (`cihub.services.configuration`).
- [x] Add report summary service for GUI consumption (`cihub.services.report_summary`).
- [x] Move CI execution core into services layer; keep CLI as thin adapter.

### 8c) Core Modularization (Phase 5)

- [x] Move `badges.py`, `ci_report.py`, and `reporting.py` into `cihub/core/` with facades.
- [x] Split `ci_runner.py` into `cihub/core/ci_runner/` with facades.
- [x] Split `aggregation.py` into `cihub/core/aggregation/` with facades.
- [x] Update `cihub/core/__init__.py` re-exports for new core modules.
- [ ] Run targeted tests for core modularization changes.

### 8d) CLI Parser Modularization (Phase 6)

- [x] Split CLI parser definitions into `cihub/cli_parsers/` without CLI surface changes.
- [x] Run CLI help snapshot check after parser split.
- [x] Add parser group registry to centralize command registration order.
- [x] Add CLI parser contract tests (handler wiring + JSON flag coverage).
- [x] Deduplicate CLI aliases to prevent drift (`doctor`/`preflight`).
- [x] Add `CIHUB_DEBUG` env toggle for developer tracebacks (opt-in).
- [x] Add `CIHUB_VERBOSE` env toggle for tool output streaming/log capture (opt-in).
- [x] Add `CIHUB_DEBUG_CONTEXT` env toggle for CLI context blocks (opt-in).

### 8e) Modularization Guardrails (CLI-First)

- [x] Canonicalize `load_ci_config`/`load_hub_config` to delegate to `cihub.config.loader` validation.
- [x] Remove `cihub.cli` imports from command modules (commands use services/utils only).
- [x] Enforce Stage 2 AST layer boundaries (core/services/commands) in tests.

### 8b) Config Ergonomics (Shorthand + Threshold Presets)

- [x] Expand shorthand booleans to enabled sections (reports, notifications, kyverno, optional features, hub_ci).
- [x] Add `thresholds_profile` presets with explicit `thresholds` overrides.
- [x] Split CVSS thresholds for OWASP/Trivy and add workflow input parity.

### 9) Triage, Registry, and LLM Bundles (New)

> **Implementation Note:** Triage bundles + prompt pack exist behind `CIHUB_EMIT_TRIAGE` env toggle.
> Centralized registry + LLM diff outputs remain TODO.

- [x] Define `cihub-triage-v1` schema with severity/blocker fields and stable versioning. *(Version constant in code; formal JSON Schema deferred to `--validate-schema` item below)*
- [x] Implement `cihub triage` to emit:
  - `.cihub/triage.json` (full bundle)
  - `.cihub/priority.json` (sorted failures)
  - `.cihub/triage.md` (LLM prompt pack)
  - `.cihub/history.jsonl` (append-only run log)
- [ ] Standardize artifact layout under `.cihub/artifacts/<tool>/` with a small manifest.
- [ ] Extend `cihub triage` to surface docs drift findings from `.cihub/tool-outputs/` (category `docs`). See **6b) Documentation Automation**.
- [ ] Normalize core outputs to standard formats (SARIF, Stryker mutation, pytest-json/CTRF, Cobertura/lcov, CycloneDX/SPDX).
- [ ] Add severity map defaults (0-10) with category + fixability flags.
- [ ] Add `cihub fix --safe` (deterministic auto-fixes only).
- [ ] Add `cihub assist --prompt` (LLM-ready prompt pack from triage bundle).
- [ ] Define registry format and CLI (`cihub registry list/show/set/diff/sync`). NOTE: this will add `config/registry.json` (Ask First).
- [ ] Add drift detection by cohort (language + profile + hub) and report variance against expected thresholds.
- [ ] Add registry versioning + rollback (immutable version history).
- [ ] Add triage schema validation (`cihub triage --validate-schema`).
- [ ] Add retention policies (`cihub triage prune --days N`).
- [ ] Add aggregate pass rules (composite gating).
- [ ] Add post-mortem logging for drift incidents.
- [ ] Add continuous reconciliation (opt-in auto-sync).
- [ ] Add RBAC guidance (defer to GitHub permissions for MVP).
- [ ] Add DORA metrics derived from history (optional).

### 10) Maintainability Improvements (From 2026-01-04 Audit)

> **Audit Source:** Multi-agent CLI/services/workflow audit + web research.
> **Principle:** All fixes stay in Python (CLI-first per ADR-0031). No composite actions or workflow logic.

**Code Deduplication (High Priority):**
- [ ] Consolidate `_tool_enabled()` — 5 implementations → 1 canonical in `cihub/config/loader/core.py`
  - Locations: `config/loader/core.py`, `services/ci_engine/helpers.py`, `commands/report/helpers.py`, `commands/run.py`, `commands/config_outputs.py`
  - 54 usages across codebase; any bug fix currently requires 5 updates
- [ ] Refactor gate evaluation (`services/ci_engine/gates.py`) — extract pattern, data-drive config
  - Current: 260 lines with 28 repetitive threshold checks
  - Target: ~100 lines with generic `check_metric_gate()` helper

**Test Coverage (High Priority):**
- [ ] Expand `test_services_ci.py` — 2 tests → 20+ tests
  - Missing: Python/Java branching, tool execution, gate evaluation, notifications, env overrides
- [ ] Add dedicated unit tests for `services/ci_engine/helpers.py` (272 lines, no test file)
- [ ] Add dedicated unit tests for `services/ci_engine/gates.py` (260 lines, no test file)

**CLI Consistency:**
- [ ] Enable `--json` flag for `hub-ci` subcommands (47 commands currently blocked)
  - Issue: `hub_ci.py` explicitly deletes the JSON flag parameter
- [ ] Require subcommand for `cihub config` and `cihub adr` (currently optional, confusing UX)

**Architecture (Medium Priority):**
- [ ] Extract Language Strategies — `cihub/core/languages/` with polymorphic pattern
  - Eliminates 38+ `if language == "python"` / `elif language == "java"` branches
  - Files: `base.py` (ABC), `python.py`, `java.py`, `registry.py`
  - See `active/CLEAN_CODE.md` Part 2.1 for design

**Workflow Security (Quick Fix):**
- [ ] Pin `step-security/harden-runner` versions (21 unpinned uses across workflows)

**Centralization & Boundaries (From Audit):**
- [ ] Env/context wrapper — `cihub/utils/github.py:GitHubContext`
  - Centralizes 17 files with direct `os.environ.get("GITHUB_*")` reads
  - Property accessors for common values (repo, sha, ref, actor, etc.)
  - Lint/test to enforce usage (no direct `GITHUB_*` reads in commands)
- [ ] Runner/adapter boundaries — All subprocess execution in `cihub/core/ci_runner/shared.py`
  - Adapters build specs; strategies orchestrate; no ad-hoc `subprocess.run` in commands
  - Add lint/test to forbid subprocess imports outside `ci_runner/`
- [ ] Output normalization — Forbid `print()` in command modules
  - Commands return `CommandResult` with summary/details/problems
  - Human formatting only in `cli.py` layer
  - Add lint/test that walks commands/ and flags print statements

**Performance & Enforcement (From Audit):**
- [ ] Performance guardrails for `cihub docs stale` / `cihub docs audit`
  - Target: <5s on ~28k-line docs corpus
  - Add simple perf test to keep `cihub check --audit` usable
- [ ] "No inline logic" workflow guard
  - Lint that flags multi-line `run: |` blocks in workflows (except allowlist: checkout, setup-python, pip install)
  - Reinforces ADR-0031 without composite actions
  - Wire into `cihub docs audit` or `cihub check --full`

---

## Documentation Consolidation Rules

- Do not duplicate CLI help text in markdown; generate it.
- Do not hand-write config field docs; generate from schema.
- If code and docs conflict, code wins and docs must be updated.

---

## Scope Guardrails

1. No large refactors (renames, src/ move, etc.) until workflow migration stabilizes.
2. No deleting docs; archive instead.
3. ADR alignment comes before cleanup decisions.
4. Fixtures repo stays for CI/regression; local dev uses scaffold/smoke.
5. Active design docs live in `docs/development/active/` and must be listed in `status/STATUS.md`.
6. When a design doc is implemented, move to `docs/development/archive/` with a superseded header.

---

## Open Questions

- Where should the long-term audit ledger live (root vs docs/development)?
- Which generated doc toolchain do we want (custom CLI, sphinx-click, or minimal generator)?
- Do we want a CI gate for ADR drift detection (warn vs fail)?

---

## Definition of Done (Near-Term)

- [x] CLI helpers committed and passing tests (`cihub check`, `preflight`, `scaffold`, `smoke`).
- [x] `docs/reference/CLI.md` and `docs/reference/CONFIG.md` generated from code.
- [x] `docs/README.md` exists and clarifies doc hierarchy.
- [x] Guides consolidated into a single entry point (`GETTING_STARTED.md`).
- [x] ADRs updated to reflect `hub-ci.yml` wrapper and CLI-first execution.
- [ ] Smoke test and targeted pytest results recorded.
- [x] Local validation checklist documented and used before push (`make check` + GETTING_STARTED.md).
- [x] Pre-commit hooks: actionlint, zizmor, lychee.
- [x] CLI automation: `docs links` (with `--external` flag, fallback to Python).
- [x] CLI automation: `adr new/list/check` commands.
- [ ] CLI automation: `config validate`, `audit` (remaining).

---

## Post v1.0 Backlog

> **Explicitly deferred.** These items are valuable but not blocking v1.0 release.
> Move to v1.0 Cutline when ready to prioritize.

### Registry & Versioning
- [ ] Implement registry CLI + versioning/rollback (`cihub registry list/show/set/diff/sync`)
- [ ] Add `config/registry.json` (Ask First before implementing)
- [ ] Add drift detection by cohort (language + profile + hub)
- [ ] Add registry versioning + rollback (immutable version history)

### Triage Enhancements

**Remote Run Analysis (CLI-First, ADR-0035 aligned):**

> **Status:** Initial implementation exists (`--run`, `--artifacts-dir`, `--repo` flags added).
> Needs enhancement for multi-repo/matrix runs and artifact-first strategy.

- [x] Add `cihub triage --run <run_id>` — Basic implementation (log parsing fallback)
- [x] Add `cihub triage --artifacts-dir <path>` — Offline mode (basic support)
- [x] Add `cihub triage --repo <owner/repo>` — Target different repository

**Production Enhancements (Required for real workflows):**
- [ ] **Artifact-first strategy**: Download artifacts before falling back to logs
  - `gh run download <run_id>` to fetch `*-ci-report` artifacts
  - Parse `report.json`, `summary.md`, `tool-outputs/*.json` from each artifact
  - Only fall back to `--log-failed` if no artifacts exist
- [ ] **Multi-repo/matrix support**: Handle orchestrator runs with multiple repos
  - `hub-run-all` uploads one artifact per repo (e.g., `repo-name-ci-report`)
  - `hub-orchestrator` uploads dispatch metadata
  - Produce one triage bundle per repo OR a merged aggregate view
  - Add `--aggregate` flag to merge all repo bundles into single triage
- [ ] **CI parity**: Same bundle shape for local and remote
  - Local: reads from `.cihub/report.json`
  - Remote: downloads to temp dir, reads same structure
  - Both produce identical `triage.json`, `priority.json`, `triage.md`
- [ ] **Auth/opt-in**: Require explicit flag/env for remote fetch
  - Default mode stays local/offline
  - `--run` requires `GH_TOKEN` or authenticated `gh` CLI
  - Add `--no-fetch` to skip artifact download and use cached
- [ ] **Graceful gaps**: Handle missing data properly
  - If `report.json` missing: add `missing_report` failure, note any tool outputs found
  - If artifacts AND logs missing: fail with clear message
  - If some repos succeeded and some failed: include both in aggregate
- [ ] **Performance/safety**:
  - Limit download size (skip artifacts > 100MB)
  - Allow `--artifacts-dir` to reuse already-downloaded artifacts
  - Add timeouts for remote operations (default 60s)
- [ ] Add `cihub triage --workflow <name>` — Analyze latest failure from named workflow
- [ ] Add `cihub triage --branch <branch>` — Analyze latest failure on branch

**Schema & Retention:**
- [ ] Add triage schema validation (`cihub triage --validate-schema`)
- [ ] Add retention policies (`cihub triage prune --days N`)
- [ ] Add aggregate pass rules (composite gating)
- [ ] Add post-mortem logging for drift incidents
- [ ] Add continuous reconciliation (opt-in auto-sync)

**Output Normalization:**
- [ ] Normalize core outputs to standard formats (SARIF, Stryker, pytest-json, Cobertura, CycloneDX)
- [ ] Add severity map defaults (0-10) with category + fixability flags
- [ ] Add `cihub fix --safe` (deterministic auto-fixes only)
- [ ] Add `cihub assist --prompt` (LLM-ready prompt pack from triage bundle)

### Governance & Metrics
- [ ] Add RBAC guidance (defer to GitHub permissions for MVP)
- [ ] Add DORA metrics derived from history (optional)

### Optional Tooling
- [ ] Evaluate `act` integration for local workflow simulation (document limitations)
- [ ] Doc manifest (`docs_manifest.json`) for LLM context (path, category, generated flag, last-reviewed)

### Tooling Expansion (Security + Quality)
- [ ] DAST (ZAP) CLI-first toggle + runner:
  - Add `python.tools.zap` config + schema/defaults
  - Add CLI runner (`cihub ci`/`cihub run zap`) and tool-outputs capture
  - Replace workflow inline action usage with CLI invocation
  - Add report summaries + dashboard metrics for ZAP findings
  - Update templates/profiles + `tests/test_templates.py`
- [ ] API schema testing via Schemathesis (`python.tools.schemathesis`), CLI runner + report metrics
- [ ] Pre-commit integration (`cihub init --pre-commit`) + config template support
- [ ] API docs generation (`cihub docs generate --api` via pdoc or equivalent)
- [ ] Deep linting (`python.tools.pylint`) as optional complement to Ruff
- [ ] Quality dashboards (SonarQube integration; optional, infra-dependent)
- [ ] Premium DAST option (StackHawk; optional)

### PyQt6 GUI (Phase 2)
- [ ] See `active/PYQT_PLAN.md` for full scope — deferred until CLI stabilizes
