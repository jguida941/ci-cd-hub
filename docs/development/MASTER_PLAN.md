# CI/CD Hub - Master Plan

**Status:** Canonical plan for all active work
**Last Updated:** 2026-01-09 (SYSTEM_INTEGRATION_PLAN.md consolidation)

> This is THE plan. All action items live here. STATUS.md tracks current state.

---

## CURRENT PRIORITY AT A GLANCE

| Priority | Document | Status | Next Action |
|----------|----------|--------|-------------|
| **#1 ** | CLEAN_CODE.md | ~90% | Part 5.3: Special-Case Handling |
| **#2 ** | SYSTEM_INTEGRATION_PLAN.md | Active | Phase 2-6 (schema, wizard, registry parity) |
| **#3 ** | TEST_REORGANIZATION.md | PLANNED | Resolve blockers first |
| **#4 ** | DOC_AUTOMATION_AUDIT.md | ~80% | Part 13 R/U/W/X + Q headers + specs hygiene + guide cmd validation |
| **#5 ** | TYPESCRIPT_CLI_DESIGN.md | Planning | Wait for CLEAN_CODE.md 100% |
| **#6 ** | PYQT_PLAN.md | DEFERRED | Wait for all above |

---

## Purpose

Single source of truth for **priorities, scope, and sequencing**. Individual planning docs own the **detailed implementation plans**.

### Document Hierarchy (Updated 2026-01-06)

```
MASTER_PLAN.md
├── WHAT to do and IN WHAT ORDER
├── High-level status tracking
└── Cross-cutting architectural decisions

Individual Planning Docs (Priority Order)
├── #1 CLEAN_CODE.md → HOW to implement architecture improvements
├── #2 SYSTEM_INTEGRATION_PLAN.md → HOW to fix registry/wizard disconnect
├── #3 TEST_REORGANIZATION.md → HOW to restructure 2100+ tests
├── #4 DOC_AUTOMATION_AUDIT.md → HOW to implement doc automation
├── #5 TYPESCRIPT_CLI_DESIGN.md → HOW to build TypeScript CLI
└── #6 PYQT_PLAN.md → HOW to build GUI (deferred)
```

**Rule:** When MASTER_PLAN.md and an individual doc conflict on implementation details, the **individual doc wins**. MASTER_PLAN.md may be stale on details but should be current on priorities.

---

## Active Design Docs - Priority Order

> **Work on these IN ORDER. Each doc blocks the next.** Updated 2026-01-06.

### Priority 1: CLEAN_CODE.md (CURRENT - Foundation)

**Status:** ~90% complete | **Blocks:** Everything else

```
docs/development/active/CLEAN_CODE.md
```

Must complete **before** starting other docs:
- [x] Part 2.2: Centralize Command Output [x] **DONE** (45→7 prints, 84% reduction)
- [x] Part 2.7: Consolidate ToolResult [x] **DONE** (unified in `cihub/types.py`)
- [x] Part 5.2: Mixed Return Types [x] **DONE** (all 47 commands → pure CommandResult)
- [x] Part 9.3: Schema Consolidation [x] **DONE** (sbom/semgrep → sharedTools, toolStatusMap extracted)
- [x] Part 7.1: CLI Layer Consolidation [x] **DONE** (factory in common.py, findings done in Part 2.2/5.2)
- [x] Part 7.2: Hub-CI Subcommand Helpers [x] **DONE** (helpers exist, ensure_executable now used)
- [x] Part 7.3: Utilities Consolidation [x] **DONE** (project.py, github_context.py, safe_run() + 34 migrations)
- [ ] Part 5.3: Special-Case Handling ← **CURRENT** (move to tool adapters)
- [ ] Part 7.4: Core Module Refactoring
- [ ] Part 7.5: Config/Schema Consistency
- [ ] Part 7.6: Services Layer
- [ ] Part 9.1: Scripts & Build System
- [ ] Part 9.2: GitHub Workflows Security

**Why first:** Python CLI JSON output must be clean before TypeScript CLI can parse it.

### Priority 2: SYSTEM_INTEGRATION_PLAN.md (Consolidated Architecture Fix)

**Status:** Consolidated (13-agent comprehensive analysis) | **Depends on:** CLEAN_CODE.md ~90%+ | **Blocks:** TEST_REORGANIZATION

```
docs/development/active/SYSTEM_INTEGRATION_PLAN.md
```

> **Note:** This consolidates the former REGISTRY_AUDIT_AND_PLAN.md, WIZARD_IMPROVEMENTS.md, and COMPREHENSIVE_SYSTEM_AUDIT.md into a single actionable plan.

Core implementation needed:
- [x] Phase 0: Safety + JSON purity (registry keys, --json guard/tests)
- [x] Phase 1: Critical fixes & CLI wrappers (min_score normalization, hub-ci wrappers, cihub block)
- [ ] Phase 2: Registry schema + service (full config scope)
- [ ] Phase 3: Registry bootstrap + drift detection
- [ ] Phase 4: Wizard parity + profile integration
- [ ] Phase 5: CLI management commands (profile/registry/tool/threshold/repo)
- [ ] Phase 6: Schema extensibility (custom tools end-to-end)

**Why second:** Fixes the wizard/registry disconnect BEFORE test reorganization validates it. The multi-agent audits revealed critical gaps:
- Registry only tracks 3 of 40+ values
- Wizard creates configs but never updates registry.json
- Wizard doesn't surface existing 12 profiles
- CLI management surface is incomplete (audit required)

### Priority 3: TEST_REORGANIZATION.md (After Registry Integration)

**Status:** PLANNED (10-12 day blockers identified) | **Depends on:** CommandResult migration + Registry fix

```
docs/development/active/TEST_REORGANIZATION.md
```

Blockers to resolve first:
- [ ] `cihub hub-ci thresholds` CLI command not implemented
- [ ] Schema blocks per-module overrides (`additionalProperties: false`)
- [ ] 3 automation scripts must be created

**Why third:** Tests need to validate registry integration alongside command outputs.

### Priority 4: DOC_AUTOMATION_AUDIT.md (Can parallel with TEST_REORGANIZATION)

**Status:** ~80% implemented (optional artifact outputs now available) | **Depends on:** Stable CLI surface

```
docs/development/active/DOC_AUTOMATION_AUDIT.md
```

Core MVP:
- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) - Modularized package (6 modules, 63 tests including 15 Hypothesis)
 - [x] Optional `--output-dir`, `--tool-output`, `--ai-output` flags for artifact outputs [x] (2026-01-09)
- [x] `cihub docs audit` - [x] **MOSTLY COMPLETE** (2026-01-09) - Modular package (7 modules, 22 tests)
 - [x] Lifecycle validation (J/L/N): active/STATUS.md sync, ADR metadata, references [x]
 - [x] Part 13.S: Duplicate task detection (fuzzy matching) [x]
 - [x] Part 13.T: Timestamp freshness validation [x]
 - [x] Part 13.V: Placeholder detection [x]
 - [ ] Part 12.Q: Universal doc header enforcement
 - [ ] Specs hygiene (Part 12.J remainder)
- [x] Default wiring into `cihub check --audit` [x] (with skip_references, skip_consistency for fast lane)
- [ ] Part 13 remaining - Metrics drift (R), checklist-reality (U), cross-doc (W), CHANGELOG (X)

**Why fourth:** Documentation automation needs stable command signatures.

### Priority 5: TYPESCRIPT_CLI_DESIGN.md (After CLEAN_CODE complete)

**Status:** Planning | **Depends on:** CLEAN_CODE.md (100% - explicit prerequisite)

```
docs/development/active/TYPESCRIPT_CLI_DESIGN.md
```

Explicit prerequisite in doc:
> "DO NOT START THIS UNTIL CLEAN_CODE.md IS COMPLETE."

**Why fifth:** TypeScript CLI consumes Python CLI JSON; needs clean output.

### Priority 6: PYQT_PLAN.md (Deferred)

**Status:** Reference only | **Depends on:** Everything above

```
docs/development/active/PYQT_PLAN.md
```

**Why last:** GUI wrapper needs all CLI commands stable and tested.

### Dependency Graph

```
┌─────────────────────────┐
│ CLEAN_CODE.md │ ◄─── START HERE (#1)
│ (Foundation ~90%) │
└───────────┬─────────────┘
 │
 ▼
┌─────────────────────────┐
│ REGISTRY_AUDIT_AND_ │ ◄─── NEW (#2)
│ PLAN.md (Architecture) │
└───────────┬─────────────┘
 │
 ┌───────┴───────┬─────────────────┐
 ▼ ▼ ▼
┌───────────┐ ┌──────────────┐ ┌──────────────────────┐
│ TEST_ │ │ DOC_AUTO_ │ │ TYPESCRIPT_CLI_ │
│ REORG.md │ │ AUDIT.md │ │ DESIGN.md │
│ (#3) │ │ (#4) │ │ (#5) │
└─────┬─────┘ └──────────────┘ └──────────┬───────────┘
 │ │
 └───────────────┬───────────────────┘
 ▼
 ┌───────────────┐
 │ PYQT_PLAN.md │
 │ (#6) │
 └───────────────┘
```

---

## v1.0 Cutline

> **What must ship for v1.0 vs what is explicitly deferred.**
> Items below the cutline move to "Post v1.0 Backlog" at the end of this document.

### Quick Wins (Do First)

**CLI Commands:**
- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) Modularized package, 63 tests
- [x] `cihub docs audit` - [x] **MOSTLY COMPLETE** (2026-01-09) Lifecycle + Part 13.S/T/V, 22 tests
- [ ] `cihub config validate` - Validate hub configs
- [ ] `cihub audit` - Umbrella command (docs check + links + adr check + config validate)
- [ ] `--json` flag for all commands including hub-ci subcommands

**Documentation:**
- [ ] Generate `docs/reference/TOOLS.md` from `cihub/tools/registry.py`
- [ ] Generate `docs/reference/WORKFLOWS.md` from `.github/workflows/*.yml`
- [ ] Plain-text reference scan for stale `docs/...` strings
- [ ] Universal header enforcement for manual docs
- [x] `.cihub/tool-outputs/` artifacts for doc automation [x] (optional via `--output-dir`, `--tool-output`, `--ai-output`)
- [ ] Tooling integration checklist: toggle -> CLI runner (no inline workflow logic) -> tool-outputs -> report summaries/dashboards -> templates/profiles -> docs refs -> template sync tests

**Clean Code:** *(See `active/CLEAN_CODE.md` for details - audit updated 2026-01-05)*
- [x] `_tool_enabled()` consolidation (5 implementations → 1 canonical) [x]
 - Added `tool_enabled()` to `cihub/config/normalize.py` as canonical implementation
 - Updated 4 call sites to delegate to canonical function
- [x] Gate-spec enforcement wiring (ThresholdSpec evaluation in gates.py) [x]
 - Added `_check_threshold()` helper to gates.py
 - Defined 27 ThresholdSpecs (Python: 15, Java: 12) in gate_specs.py
 - Wired 26 threshold checks (Python: 14, Java: 12) to use `evaluate_threshold` from gate_specs
 - All 155 gate-related tests pass (test_ci_engine.py + test_gate_specs.py); full suite 1804 tests pass
- [x] Language strategy extraction (Python/Java) - Complete [x]
 - Created `cihub/core/languages/` with base.py, python.py, java.py, registry.py
 - Delegation pattern: strategies delegate to existing `_run_*_tools()` functions
 - 33 tests covering registry, strategies, build tool detection, language detection
 - Refactored `run_ci()` to use strategy as primary dispatch
 - Updated `helpers.py` to use `strategy.get_default_tools()`
 - All 1837 tests pass
- [x] Hub-CI CommandResult migration (43 functions → return CommandResult) - **Complete** [x]
 - [x] validation.py: 8 functions migrated [x]
 - [x] security.py: 6 functions migrated [x]
 - [x] smoke.py: 4 functions migrated [x]
 - [x] python_tools.py: 3 functions migrated [x]
 - [x] java_tools.py: 6 functions migrated [x]
 - [x] release.py: 16 functions migrated [x]
 - Router bug fixed (CommandResult vs int comparison)
- [x] Expand CI-engine tests (2 → 151) [x] - 118 CI engine tests + 33 strategy tests
- [x] Testing framework improvements [x] (See `active/CLEAN_CODE.md` Part 10)
 - [x] Phase T1: conftest.py, pytest-xdist, hypothesis
 - [x] Phase T2: Parameterized tests (5 files refactored)
 - [x] Phase T3: Property-based testing (12 Hypothesis tests)
 - **Total: 2120 tests passing** *(updated 2026-01-06)*
- [x] Output normalization - OutputRenderer infrastructure [x] (see **Architecture Consolidation** below)
 - [x] Contract enforcement test added (`test_command_output_contract.py`) - prevents regression
 - [x] **Migrated 13 major files** (~198 prints → CommandResult):
 - adr.py (16), triage.py (34), secrets.py (32), templates.py (22), pom.py (21)
 - dispatch.py (10), config_cmd.py (9), update.py (8), smoke.py (8), discover.py (8)
 - docs.py (10), new.py (10), init.py (10)
 - [x] **Code review fixes** (2026-01-05):
 - detect.py: Pure CommandResult return (no conditional JSON mode)
 - validate.py: Added YAML parse error handling (yaml.YAMLError, ValueError)
 - smoke.py: Fixed TemporaryDirectory resource leak
 - discover.py: Reordered empty check before GITHUB_OUTPUT write
 - cli.py: Error output routes to stderr (CLI best practice)
 - [x] ~~TODO: Migrate remaining 45 print() calls in 12 files~~ [x] **DONE** (45→7, 84% reduction)

**Test Reorganization:** *(See `active/TEST_REORGANIZATION.md` for design)*
- [ ] 2100+ tests currently in flat `tests/` directory need restructuring
- [ ] 5-agent audit identified ~10-12 days blockers before Phase 1 can start:
 - `cihub hub-ci thresholds` CLI command not implemented
 - Schema blocks per-module overrides (`additionalProperties: false`)
 - 3 automation scripts must be created
 - 35/78 (45%) test files need new categories beyond proposed structure

**Quality Gate Consistency:**
- [ ] Summary vs report validator: compare `summary.md` gate rows to `report.json` + `tools_ran/tools_success`
- [ ] Self-validate after `cihub ci`: run `cihub report validate --strict` on `report.json` + `summary.md`
- [ ] Enforce report validation in `cihub check --audit` and `cihub smoke --full`
- [ ] CI gate evaluation must fail/warn when `tests_total == 0`
- [ ] Contract test: `gates.py`, `reporting.py`, and `report_validator` agree on outcomes
- [ ] Configured-but-not-run policy: decide warning vs hard-fail and enforce consistently
- [ ] `fail_on_not_run` policy flag (global + per-tool) with enforcement in gates/summary/triage
- [ ] Threshold completeness rule: no `-` values in summaries; validator fails on missing thresholds
- [ ] Gate result semantics: decide `tools_success` meaning vs adding `gate_results` block
- [ ] Threshold sanity checks: warn/fail for permissive production thresholds (fixtures exempt)
- [x] Artifact-first triage (`cihub triage --run/--workflow/--branch`) with report validation + mismatch warnings [x]
- [x] Artifact evidence audit in triage (non-empty tool outputs, expected fields) [x]
- [x] Multi-report triage aggregation (`cihub triage --multi --reports-dir`) [x]
- [x] Per-tool evidence (configured/ran/required/result) with human-readable explanations [x]
- [ ] Gate toggle visibility in summaries (expose effective gate flags or load config alongside report)
- [x] Build tool status: reflect real build state in Tools Enabled + gates (not always Ran=true) [x]
- [x] CVSS parsing + gating: extract max CVSS from OWASP/Trivy reports and enforce `*_cvss_fail` [x]
- [x] JSON schema validation at runtime (`cihub report validate --schema`) [x]

**Security/CI Hygiene:**
- [ ] Pin `step-security/harden-runner` versions (21 uses)
- [ ] Standardize all action version pins
- [ ] Workflow input contract tests: ensure `.github/workflows/*-ci.yml` cover all `TOOL_KEYS` + `THRESHOLD_KEYS`
- [ ] Template artifact guard: templates must upload `report.json` + `.cihub/tool-outputs/*`
- [x] CommandResult CI enforcement: `cihub hub-ci enforce-command-result` [x] (ADR-0042)
 - Added CLI command to detect print() calls in commands/
 - Added workflow job `enforce-command-result` to hub-production-ci.yml
 - Enforces max 7 allowed prints (intentional exceptions documented)
- [x] Config validation order fix [x] (ADR-0047)
 - Validate BEFORE normalize at each config layer
 - Catches invalid input that normalization would mask
 - Clear error messages with layer names
- [ ] Subprocess timeout policy implementation (ADR-0045)
 - 33+ subprocess calls missing timeouts identified in INCONSISTENCY.md
 - Tiered timeouts: Quick (30s), Network (120s), Build (600s), Extended (900s)

### Heavy Lifts (After Quick Wins)

- [x] Output/summary context wrapper (`OutputContext` for GITHUB_OUTPUT/GITHUB_STEP_SUMMARY) [x]
- [ ] Env/context wrapper (`GitHubEnv` for 17 other `GITHUB_*` reads - extend `github_context.py`)
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

> WARNING: **REGISTRY ARCHITECTURE GAP (2026-01-06):** The registry system code (`registry_service.py`, `registry.schema.json`) is currently INCOMPLETE and should NOT be considered canonical until REGISTRY_AUDIT_AND_PLAN.md Parts 4-8 are implemented. The audit found:
> - Registry only tracks 3 of 47+ values
> - Wizard ↔ Registry are disconnected
> - Schema blocks extensibility with `additionalProperties: false`
>
> **Until fixed:** Follow `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` (archived) for registry architecture reference.

## References (Background Only)

**Active Design Docs** (in-progress designs, listed in `status/STATUS.md`):
- `docs/development/active/CLEAN_CODE.md` (architecture improvements: polymorphism, encapsulation)
- `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` (wizard↔registry integration, schema expansion - **archived**)
- `docs/development/active/TEST_REORGANIZATION.md` (test suite restructuring: 2100+ tests → unit/integration/e2e)
- `docs/development/active/DOC_AUTOMATION_AUDIT.md` (doc automation design: `cihub docs stale`, `cihub docs audit`)
- `docs/development/active/TYPESCRIPT_CLI_DESIGN.md` (TypeScript interactive CLI - consumes Python CLI as backend)
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

### CLI as Headless API (Architecture Principle)

> **Added 2026-01-05:** This principle is critical for understanding why CLI commands shouldn't be restructured.

The Python CLI is designed as a **headless API backend** for future frontends:

1. **TypeScript CLI** (`docs/development/active/TYPESCRIPT_CLI_DESIGN.md`) maps slash commands to Python commands:
 - `/fix-pom` → `cihub fix-pom --json`
 - `/setup-secrets` → `cihub setup-secrets --json`
 - `/config outputs` → `cihub config-outputs --json`

2. **PyQt6 GUI** (`docs/development/active/PYQT_PLAN.md`) calls Python CLI programmatically:
 - `cihub fix-pom`, `cihub fix-deps`, `cihub setup-secrets`, `cihub setup-nvd`
 **PYQT6 Deferred for now**

3. **GitHub Workflows** call CLI commands directly:
 - `hub-ci.yml`: `cihub config-outputs --repo . --github-output`
 - `hub-production-ci.yml`: 15+ `cihub hub-ci *` subcommands

**Implication:** CLI command names are **stable API contracts**. Restructuring (e.g., `setup-secrets` → `setup secrets`) would break:
- TypeScript CLI command mapping
- PyQt GUI subprocess calls, **pyqt6 deferred for now**
- GitHub workflow steps
- 40+ documentation files

**Safe changes only:**
- Help text wording
- `--help` output groupings
- Swapping `doctor`/`preflight` prominence (neither used in workflows/UIs)

See `CLEAN_CODE.md` Part 5.4 for full audit details.

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
- [ ] Review ADR-0005 (Dashboard) status - still "Proposed" after 2+ weeks.
- [ ] Clarify ADR-0035 timeline - which features are v1 vs deferred.
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
- [x] `cihub docs links` - Check internal doc links (offline by default, `--external` for web)
- [x] `cihub adr new <title>` - Create ADR from template with auto-number
- [x] `cihub adr list` - List all ADRs with status
- [x] `cihub adr check` - Validate ADRs reference valid files
- [x] `cihub verify` - Contract check for caller templates and reusable workflows (optional remote/integration modes)
- [x] `cihub hub-ci badges` - Generate/validate CI badges from workflow artifacts.
- [ ] `cihub config validate` (or `cihub validate --hub`) - Validate hub configs (resolves validate ambiguity)
- [ ] `cihub audit` - Umbrella: docs check + links + adr check + config validate
- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) Modularized package, 63 tests. Design: `active/DOC_AUTOMATION_AUDIT.md`
- [ ] `cihub docs workflows` - Generate workflow tables from `.github/workflows/*.yml` (replaces manual guides/WORKFLOWS.md)
- [x] `cihub docs audit` - [x] **MOSTLY COMPLETE** (2026-01-09) Wired into `cihub check --audit`:
 - [x] Every doc in `status/STATUS.md` Active Design Docs table must exist under `development/active/` [x]
 - [x] Every file under `development/active/` must be listed in STATUS.md [x]
 - [x] Files under `development/archive/` must have a superseded header [x]
 - [x] Plain-text reference scan for `docs/...` strings [x]
 - [x] Part 13.S: Duplicate task detection [x]
 - [x] Part 13.T: Timestamp freshness validation [x]
 - [x] Part 13.V: Placeholder detection [x]
 - [ ] Path changes require docs/README.md + status/STATUS.md updates (not enforced yet)
 - [ ] Universal doc header enforcement (Part 12.Q)
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
> **Status:** ~80% complete (Priority #4)

- [x] `cihub docs stale` - [x] **COMPLETE** (2026-01-06) Modularized package (6 modules, 63 tests including 15 Hypothesis)
 - [x] Python AST symbol extraction (base vs head comparison) [x]
 - [x] Schema key path diffing [x]
 - [x] CLI surface drift detection (help snapshot comparison) [x]
 - [x] File move/delete detection (`--name-status --find-renames`) [x]
 - [x] Output modes: human, `--json`, `--ai` (LLM prompt pack) [x]
- [x] `cihub docs audit` - [x] **MOSTLY COMPLETE** (2026-01-09) Modular package (7 modules, 22 tests):
 - [x] Validate `active/` ↔ `STATUS.md` sync [x]
 - [x] Validate `archive/` files have superseded headers [x]
 - [x] Plain-text reference scan for `docs/...` strings [x]
 - [x] ADR metadata lint (Status/Date/Superseded-by) [x]
 - [x] Part 13.S: Duplicate task detection [x]
 - [x] Part 13.T: Timestamp freshness validation [x]
 - [x] Part 13.V: Placeholder detection [x]
 - [ ] Universal header enforcement for manual docs (Part 12.Q)
 - [ ] Specs hygiene: only `REQUIREMENTS.md` is active under `development/specs/`
- [x] `.cihub/tool-outputs/` artifacts for doc automation:
 - [x] `docs_stale.json` - Machine-readable stale reference report [x] (via `--output-dir` or `--tool-output`)
 - [x] `docs_stale.prompt.md` - LLM-ready prompt pack [x] (via `--output-dir` or `--ai-output`)
 - [x] `docs_audit.json` - Lifecycle/reference/consistency findings [x] (wired into `cihub check --audit`)
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
- [x] **Split `triage_service.py` into `cihub/services/triage/` package (1134→565 lines, 50% reduction)** [x]
 - `types.py`: ToolStatus, ToolEvidence, TriageBundle dataclasses
 - `evidence.py`: build_tool_evidence, validate_artifact_evidence
 - `detection.py`: detect_flaky_patterns, detect_test_count_regression
 - `__init__.py`: Clean facade with re-exports
 - **Reference pattern for future modularization** (see CLEAN_CODE.md Part 1.5)
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
> **Update 2026-01-06:** Triage schema bumped to `cihub-triage-v2` with `tool_evidence` and `evidence_issues` sections.
> **Registry:** See `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` for registry implementation plan (archived reference).

**Triage (Implemented):**
- [x] Define `cihub-triage-v2` schema with severity/blocker fields, tool evidence, and stable versioning. [x]
 - `tool_evidence`: per-tool configured/ran/required/result status with explanations
 - `evidence_issues`: validation warnings for tools lacking expected metrics/artifacts
 - `summary.required_not_run_count`: count of HARD FAIL (require_run but didn't run) tools
- [x] Implement `cihub triage` to emit:
 - `.cihub/triage.json` (full bundle)
 - `.cihub/priority.json` (sorted failures)
 - `.cihub/triage.md` (LLM prompt pack)
 - `.cihub/history.jsonl` (append-only run log)

**Triage Enhancements (TODO):**
- [ ] Standardize artifact layout under `.cihub/artifacts/<tool>/` with a small manifest.
- [ ] Extend `cihub triage` to surface docs drift findings from `.cihub/tool-outputs/` (category `docs`). See **6b) Documentation Automation**.
- [ ] Normalize core outputs to standard formats (SARIF, Stryker mutation, pytest-json/CTRF, Cobertura/lcov, CycloneDX/SPDX).
- [ ] Add severity map defaults (0-10) with category + fixability flags.
- [ ] Add `cihub fix --safe` (deterministic auto-fixes only).
- [ ] Add `cihub assist --prompt` (LLM-ready prompt pack from triage bundle).
- [ ] Add triage schema validation (`cihub triage --validate-schema`).
- [ ] Add retention policies (`cihub triage prune --days N`).

**Registry (See REGISTRY_AUDIT_AND_PLAN.md - Priority #2):**
> **Detailed plan:** `docs/development/archive/REGISTRY_AUDIT_AND_PLAN.md` (19-part comprehensive audit - archived)
> The registry audit identified critical gaps: wizard↔registry disconnect, only 3/47+ fields tracked, etc.

- [ ] **Part 4:** Schema redesign (tool definitions via $ref, 47+ fields)
- [ ] **Part 5:** Service layer refactor (registry_service.py expansion)
- [ ] **Part 6:** Wizard ↔ Registry integration (currently disconnected)
- [ ] **Part 7:** Boolean toggle extensibility
- [ ] **Part 8:** Sync verification implementation
- [ ] Add drift detection by cohort (language + profile + hub) and report variance against expected thresholds
- [ ] Add registry versioning + rollback (immutable version history)
- [ ] Add aggregate pass rules (composite gating)
- [ ] Add post-mortem logging for drift incidents
- [ ] Add continuous reconciliation (opt-in auto-sync)
- [ ] Add RBAC guidance (defer to GitHub permissions for MVP)
- [ ] Add DORA metrics derived from history (optional)

### 10) Maintainability Improvements (From 2026-01-04 Audit)

> **Audit Source:** Multi-agent CLI/services/workflow audit + web research.
> **Principle:** All fixes stay in Python (CLI-first per ADR-0031). No composite actions or workflow logic.

**Code Deduplication (High Priority):**
- [x] Consolidate `_tool_enabled()` - 5 implementations → 1 canonical [x] *(See Quick Wins above)*
 - Canonical `tool_enabled()` added to `cihub/config/normalize.py`
 - 4 call sites now delegate to canonical function
- [x] Refactor gate evaluation (`services/ci_engine/gates.py`) - data-driven thresholds [x] *(See Quick Wins above)*
 - Added `_check_threshold()` helper wired to `gate_specs.evaluate_threshold`
 - 16 threshold checks now use centralized evaluation

**Test Coverage (High Priority):**
- [ ] Expand `test_services_ci.py` - 2 tests → 20+ tests
 - Missing: Python/Java branching, tool execution, gate evaluation, notifications, env overrides
- [x] Add dedicated unit tests for `services/ci_engine/gates.py` [x] - 161 tests in test_ci_engine.py + test_gate_specs.py
- [ ] Add dedicated unit tests for `services/ci_engine/helpers.py` (233 lines after consolidation, limited coverage)

**CLI Consistency:**
- [ ] Enable `--json` flag for `hub-ci` subcommands (47 commands currently blocked)
 - Issue: `hub_ci.py` explicitly deletes the JSON flag parameter
- [ ] Require subcommand for `cihub config` and `cihub adr` (currently optional, confusing UX)

**Architecture (Medium Priority):**
- [x] Extract Language Strategies - `cihub/core/languages/` with polymorphic pattern [x]
 - Eliminates 38+ `if language == "python"` / `elif language == "java"` branches
 - Files: `base.py` (ABC), `python.py`, `java.py`, `registry.py`
 - 33+ tests in `test_language_strategies.py`
 - See `active/CLEAN_CODE.md` Part 2.1 for design
- [x] CLI argument factory consolidation - `cihub/cli_parsers/common.py` [x]
 - 8 factory functions: `add_output_args`, `add_summary_args`, `add_repo_args`, `add_report_args`, `add_path_args`, `add_output_dir_args`, `add_ci_output_args`, `add_tool_runner_args`
 - `hub_ci.py`: 628 → 535 lines (93 lines, 15% reduction)
 - Refactored `report.py` and `core.py` to use factories
 - 30 parameterized tests in `test_cli_common.py`
- [x] OutputContext dataclass - `cihub/utils/github_context.py` [x] *(2026-01-05)*
 - Replaces 2-step pattern: `_resolve_output_path()` + `_write_outputs()` → `ctx.write_outputs()`
 - 32 call sites migrated across 7 hub-ci files
 - 38 tests (parameterized + Hypothesis property-based)
 - See `active/CLEAN_CODE.md` Phase 2
- [x] Tool execution helpers - `cihub/commands/hub_ci/__init__.py` [x] *(2026-01-05)*
 - `ToolResult` dataclass for structured tool execution results
 - `ensure_executable()` consolidates 6 chmod patterns
 - `load_json_report()` consolidates 15+ JSON parsing patterns
 - `run_tool_with_json_report()` full tool execution + JSON parsing
 - 39 tests (parameterized + Hypothesis property-based)
- [x] Project utilities consolidation - `cihub/utils/project.py` [x] *(2026-01-05)*
 - `get_repo_name()` moved from 2 duplicates (ci_engine/helpers.py, report/helpers.py)
 - `detect_java_project_type()` moved from 2 duplicates
 - 37 tests (parameterized + Hypothesis property-based)

**Workflow Security (Quick Fix):**
- [ ] Pin `step-security/harden-runner` versions (21 unpinned uses across workflows)

**Centralization & Boundaries (From Audit):**
- [x] Output/Summary context wrapper - `cihub/utils/github_context.py:OutputContext` [x] *(2026-01-05)*
 - Centralizes GITHUB_OUTPUT/GITHUB_STEP_SUMMARY handling
 - `from_args()` factory + `write_outputs()`/`write_summary()` methods
 - 32 call sites migrated, 38 tests
- [ ] Env/context wrapper - extend `cihub/utils/github_context.py` with `GitHubEnv`
 - Centralizes 17 files with direct `os.environ.get("GITHUB_*")` reads
 - Property accessors for common values (repo, sha, ref, actor, etc.)
 - Can extend existing `github_context.py` module
 - Lint/test to enforce usage (no direct `GITHUB_*` reads in commands)
- [ ] Runner/adapter boundaries - All subprocess execution in `cihub/core/ci_runner/shared.py`
 - Adapters build specs; strategies orchestrate; no ad-hoc `subprocess.run` in commands
 - Add lint/test to forbid subprocess imports outside `ci_runner/`
- [x] Output normalization - OutputRenderer abstraction [x] (2026-01-05)
 - Commands return `CommandResult` with summary/details/problems
 - `cihub/output/renderers.py` - OutputRenderer ABC, HumanRenderer, JsonRenderer
 - `cli.py` uses `get_renderer(json_mode)` at lines 394-400
 - 35 tests in `tests/test_output_renderers.py` (parameterized + Hypothesis)
 - [x] Contract enforcement via `tests/test_command_output_contract.py` (17 tests)
 - AST-based detection of print() calls in commands/
 - Allowlist pattern for incremental migration (strangler fig)
 - Prevents regression on migrated files

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

> **Status:** Full artifact-first implementation complete. Tool evidence + multi-report aggregation implemented.

- [x] Add `cihub triage --run <run_id>` - Basic implementation (log parsing fallback)
- [x] Add `cihub triage --artifacts-dir <path>` - Offline mode (basic support)
- [x] Add `cihub triage --repo <owner/repo>` - Target different repository
- [x] Add `cihub triage --multi --reports-dir <path>` - Multi-report aggregation mode

**Artifact-First Triage (Implemented):**
- [x] **Per-tool evidence**: `tool_evidence` section in triage.json shows configured/ran/required/result status
 - `ToolStatus` enum: PASSED, FAILED, SKIPPED, REQUIRED_NOT_RUN, NOT_CONFIGURED
 - Human-readable explanations for each tool's status
 - Includes tool metrics and artifact presence info
- [x] **Artifact evidence validation**: `validate_artifact_evidence()` warns when tools lack evidence
 - Warns when ran+success but no metrics/artifacts
 - Info note when failed tool has no artifacts for debugging
- [x] **Multi-report aggregation**: `aggregate_triage_bundles()` for orchestrator runs
 - Summarizes pass/fail across N repos
 - `failures_by_tool`: which tools failed in which repos
 - `failures_by_repo`: which repos failed which tools
 - Generates markdown summary table

**Production Enhancements (Remaining):**
- [x] **Artifact-first strategy**: Download artifacts before falling back to logs [x]
 - `gh run download <run_id>` to fetch `*-ci-report` artifacts
 - Parse `report.json`, `summary.md`, `tool-outputs/*.json` from each artifact
 - Only fall back to `--log-failed` if no artifacts exist
- [x] **Multi-repo/matrix support**: Handle orchestrator runs with multiple repos [x]
 - `hub-run-all` uploads one artifact per repo (e.g., `repo-name-ci-report`)
 - `hub-orchestrator` uploads dispatch metadata
 - Produce one triage bundle per repo OR a merged aggregate view
 - `--multi --reports-dir` merges all repo bundles into single multi-triage.json
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
- [ ] Add `cihub triage --workflow <name>` - Analyze latest failure from named workflow
- [ ] Add `cihub triage --branch <branch>` - Analyze latest failure on branch

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
- [ ] Add flaky test detection + test-count drop alerts from triage history (CLI-first)

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
- [ ] See `active/PYQT_PLAN.md` for full scope - deferred until CLI stabilizes
